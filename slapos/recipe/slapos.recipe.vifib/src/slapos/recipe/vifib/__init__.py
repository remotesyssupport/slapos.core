##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import slapos.recipe.erp5
import os
import pkg_resources
import zc.buildout
import sys

class Recipe(slapos.recipe.erp5.Recipe):
  def installKeyAuthorisationApache(self, ip, port, backend, ca_conf,
      key_auth_path='/erp5/portal_slap'):
    ssl_template = """SSLEngine on
SSLVerifyClient require
RequestHeader set REMOTE_USER %%{SSL_CLIENT_S_DN_CN}s
SSLCertificateFile %(key_auth_certificate)s
SSLCertificateKeyFile %(key_auth_key)s
SSLCACertificateFile %(ca_certificate)s
SSLCARevocationPath %(ca_crl)s"""
    apache_conf = self._getApacheConfigurationDict('key_auth_apache', ip, port)
    apache_conf['ssl_snippet'] = ssl_template % ca_conf
    prefix = 'ssl_key_auth_apache'
    rewrite_rule_template = \
      "RewriteRule (.*) http://%(backend)s%(key_auth_path)s$1 [L,P]"
    path_template = pkg_resources.resource_string('slapos.recipe.erp5',
      'template/apache.zope.conf.path.in')
    path = path_template % dict(path='/')
    d = dict(
          path=path,
          backend=backend,
          backend_path='/',
          port=apache_conf['port'],
          vhname=path.replace('/', ''),
          key_auth_path=key_auth_path,
    )
    rewrite_rule = rewrite_rule_template % d
    apache_conf.update(**dict(
      path_enable=path,
      rewrite_rule=rewrite_rule
    ))
    apache_config_file = self.createConfigurationFile(prefix + '.conf',
        pkg_resources.resource_string('slapos.recipe.erp5',
          'template/apache.zope.conf.in') % apache_conf)
    self.path_list.append(apache_config_file)
    self.path_list.extend(zc.buildout.easy_install.scripts([(
      'key_auth_apache',
        'slapos.recipe.erp5.apache', 'runApache')], self.ws,
          sys.executable, self.wrapper_directory, arguments=[
            dict(
              required_path_list=[ca_conf['key_auth_certificate'],
                ca_conf['key_auth_key'], ca_conf['ca_certificate'],
                ca_conf['ca_crl']],
              binary=self.options['httpd_binary'],
              config=apache_config_file
            )
          ]))
    return 'https://%(ip)s:%(port)s' % apache_conf

  def _getZeoClusterDict(self):
    site_path = '/erp5/'
    return {
        '/': (self._requestZeoFileStorage('Zeo Server 1', 'main'),
          site_path + 'account_module'),
    }

  def installProduction(self):
    ca_conf = self.installCertificateAuthority()
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    conversion_server_conf = self.installConversionServer(
        self.getLocalIPv4Address(), 23000, 23060)
    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)
    user, password = self.installERP5()
    zodb_dir = os.path.join(self.data_root_directory, 'zodb')
    self._createDirectory(zodb_dir)
    zodb_root_path = os.path.join(zodb_dir, 'root.fs')
    ip = self.getLocalIPv4Address()
    mount_point_zeo_dict = self._getZeoClusterDict()
    zeo_conf = self.installZeo(ip)
    zodb_configuration_list = []
    known_tid_storage_identifier_dict = {}
    for mount_point, (storage_dict, check_path) in mount_point_zeo_dict.iteritems():
      known_tid_storage_identifier_dict[
        (((storage_dict['ip'],storage_dict['port']),), storage_dict['storage_name'])
        ] = (zeo_conf[storage_dict['storage_name']]['path'], check_path or mount_point)
      zodb_configuration_list.append(self.substituteTemplate(
        self.getTemplateFilename('zope-zeo-snippet.conf.in'), dict(
        storage_name=storage_dict['storage_name'],
        address='%s:%s' % (storage_dict['ip'], storage_dict['port']),
        mount_point=mount_point
        )))
    tidstorage_config = dict(host=self.getLocalIPv4Address(), port='6001')
    zodb_configuration_string = '\n'.join(zodb_configuration_list)
    zope_port = 12000
    # One Distribution Node
    zope_port +=1
    self.installZope(ip, zope_port, 'zope_distribution', with_timerservice=True,
        zodb_configuration_string=zodb_configuration_string,
        tidstorage_config=tidstorage_config)
    # Two Activity Nodes
    for i in (1, 2):
      zope_port += 1
      self.installZope(ip, zope_port, 'zope_activity_%s' % i,
          with_timerservice=True,
          zodb_configuration_string=zodb_configuration_string,
          tidstorage_config=tidstorage_config)
    # Four Web Page Nodes (Human access)
    login_url_list = []
    for i in (1, 2, 3, 4):
      zope_port += 1
      login_url_list.append(self.installZope(ip, zope_port,
        'zope_login_%s' % i, with_timerservice=False,
        zodb_configuration_string=zodb_configuration_string,
        tidstorage_config=tidstorage_config))
    login_haproxy = self.installHaproxy(ip, 15001, 'login', self.site_check_path,
        login_url_list)
    apache_login = self.installLoginApache(self.getGlobalIPv6Address(), 15000,
        login_haproxy, ca_conf['login_key'], ca_conf['login_certificate'])
    # Four Web Service Nodes (Machine access)
    service_url_list = []
    for i in (1, 2, 3, 4):
      zope_port += 1
      service_url_list.append(self.installZope(ip, zope_port,
        'zope_service_%s' % i, with_timerservice=False,
        zodb_configuration_string=zodb_configuration_string,
        tidstorage_config=tidstorage_config))
    service_haproxy = self.installHaproxy(ip, 15000, 'service',
        self.site_check_path, service_url_list)
    apache_keyauth = self.installKeyAuthorisationApache(
        self.getLocalIPv4Address(), 15500, service_haproxy, ca_conf,
        key_auth_path=self.key_auth_path)
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    kumo_conf = self.installKumo(self.getLocalIPv4Address())
    self.linkBinary()
    self.setConnectionDict(dict(
      site_url=apache_login,
      site_user=user,
      site_password=password,
      service_url=apache_keyauth,
      memcached_url=memcached_conf['memcached_url'],
      conversion_server_url='%(conversion_server_ip)s:%(conversion_server_port)s' %
        conversion_server_conf,
      # openssl binary might be removed, as soon as CP environment will be
      # fully controlled
      openssl_binary=self.options['openssl_binary'],
      # As soon as there would be Vifib ERP5 configuration and possibility to
      # call it over the network this can be removed
      certificate_authority_path=ca_conf['certificate_authority_path'],
      # as installERP5Site is not trusted (yet) and this recipe is production
      # ready expose more information
      mysql_url='%(mysql_database)s@%(ip)s:%(tcp_port)s %(mysql_user)s %(mysql_password)s' % mysql_conf,
    ))
    return self.path_list

  def installDevelopment(self):
    ca_conf = self.installCertificateAuthority()
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    conversion_server_conf = self.installConversionServer(
        self.getLocalIPv4Address(), 23000, 23060)
    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)
    user, password = self.installERP5()
    zodb_dir = os.path.join(self.data_root_directory, 'zodb')
    self._createDirectory(zodb_dir)
    zodb_root_path = os.path.join(zodb_dir, 'root.fs')
    ip = self.getLocalIPv4Address()
    zope_port = '18080'
    zope_access = self.installZope(ip, zope_port, 'zope_development',
        zodb_configuration_string=self.substituteTemplate(
          self.getTemplateFilename('zope-zodb-snippet.conf.in'),
          dict(zodb_root_path=zodb_root_path)),
          thread_amount=8, with_timerservice=True)
    service_haproxy = self.installHaproxy(ip, 15000, 'service',
        self.site_check_path, [zope_access])
    apache_keyauth = self.installKeyAuthorisationApache(
        self.getLocalIPv4Address(), 15500, service_haproxy, ca_conf,
        key_auth_path=self.key_auth_path)
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    kumo_conf = self.installKumo(self.getLocalIPv4Address())
    self.installTestRunner(ca_conf, mysql_conf, conversion_server_conf,
        memcached_conf, kumo_conf)
    self.linkBinary()
    self.setConnectionDict(dict(
      development_zope='http://%s:%s/' % (ip, zope_port),
      site_user=user,
      site_password=password,
      service_url=apache_keyauth,
      memcached_url=memcached_conf['memcached_url'],
      conversion_server_url='%(conversion_server_ip)s:%(conversion_server_port)s' %
        conversion_server_conf,
      # openssl binary might be removed, as soon as CP environment will be
      # fully controlled
      openssl_binary=self.options['openssl_binary'],
      # As soon as there would be Vifib ERP5 configuration and possibility to
      # call it over the network this can be removed
      certificate_authority_path=ca_conf['certificate_authority_path'],
      # as installERP5Site is not trusted (yet) and this recipe is production
      # ready expose more information
      mysql_url='%(mysql_database)s@%(ip)s:%(tcp_port)s %(mysql_user)s %(mysql_password)s' % mysql_conf,
    ))
    return self.path_list

  def _install(self):
    self.site_check_path = '/%s/getId' % self.site_id
    self.key_auth_path = '/%s/portal_slap' % self.site_id
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set([__name__])
    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', __name__ + '.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]
    self.path_list.append(self.killpidfromfile)
    if self.parameter_dict.get('development', 'false').lower() == 'true':
      return self.installDevelopment()
    if self.parameter_dict.get('production', 'false').lower() == 'true':
      return self.installProduction()
    raise NotImplementedError('Flavour of instance have to be given.')
