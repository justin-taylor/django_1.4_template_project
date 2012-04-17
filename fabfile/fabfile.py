from __future__ import with_statement
from fabric.api import run, env, local, cd
from fabric.context_managers import settings
from django.template.loaders.filesystem import Loader

import os

FAB_DIRECTORY = os.path.dirname(__file__)
CONF_DIRECTORY = FAB_DIRECTORY+"/conf"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

"""
TODO:
    1) setup local_settings.py in the shared directory and symlink it into current
    2) add upstart of new supervisor
"""


env.project_name = 'central.tayloredapps.org'

# the number of releases to keep in the release folder
# before deleting old releases
# set to a negative number or zero to turn this feature off
env.release_count = 5

#-------------------------------------------------------------------------------
#    ENVIRONMENTS
#-------------------------------------------------------------------------------

def development():
    from envs.development import *

def production():
    from envs.production import *
#-------------------------------------------------------------------------------
#   TASKS
#-------------------------------------------------------------------------------

def test():
    "Run the test suite and bail out if it fails"
    local("cd $(project_name); python manage.py test", fail="abort")

def deploy():
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, 
    then restart the webserver
    """
    
    set_to_new_release()

    try:
        clone_release()

    except:
        'Deleting cloned release'
        with cd("%s/releases/" % env.path):
            run("rm -rf" %  env.release)
    else: 
        deploy_release(env.release)

def deploy_release(release):
    """
    @param [String] the name of the folder to set as the current source
                    should be in the form of a timestamp YYYYMMDDHHMMSS
    """
    try:
        symlink_release(release)
        install_requirements(release)
        symlink_shared_files()
        migrate()
        restart_gunicorn()

    except Exception, e:
        print e.message
        rollback()

    finally:
        clean_old_releases()


#TODO
def initialize_server():
    """
    run the initial setup of the server

    install dependencies, setup the directory structure
    setup the virtalenv, install the nginx amd supervisor conf files
    """
    pass


#TODO
def start():
    """
    start nginx, supervisor, and gunicorn
    only if ther services have not started
    """
    pass


#TODO
def stop():
    """
    stop nginx, supervisor, and gunicorn
    """
    pass


#TODO
def restart():
    """
    restart each service
    note gunicorn will be restarted through supervisor
    """
    pass


def setup():
    """
    runs the initial setup of the django project
    and directory structure
    """

    run("cd /srv && mkdir %s" % env.project_name)
    with cd("/srv/%s" % env.project_name):
        run("virtualenv %s" % env.virtualenv_name)
        run("mkdir %s/releases" % env.virtualenv_name)

    setup_shared_directory()
    create_logs_directories()
    clone_release()
    symlink_release(env.release)
    install_requirements(env.release)
    setup_configuration_files()
    symlink_configuration_files()
    restart_nginx()


def rollback(delete = 'delete'):
    """
    @param [Tuple]

    Rolls back the application to the previous release
    and deletes the release that was last deployed

    If 'no_delete' is passed as an arg the last release deployed is not deleted
    for example: fab production rollback:no_delete
    """

    print "Rolling Back"

    with cd("%s/releases/" % env.path):
        folders = run("ls -A | tail -2")
        folders = folders.split('\r\n')

        if folders.count < 2:
            print "There is no available release to rollback to"
            return

        symlink_release(folders[0])
        install_requirements(folders[0])
        restart_gunicorn()

        if delete != 'no_delete':
            run("rm -r %s" % folders[1])


#-------------------------------------------------------------------------------
# HELPER METHODS
#-------------------------------------------------------------------------------

def set_to_new_release():
    import time
    env.release = time.strftime('%Y%m%d%H%M%S')


def clone_release():
    with cd("%s/releases/" % env.path):
        run("git clone -b %s %s %s" % (env.git_branch, env.git_repo, env.release))


def install_requirements(release):
    "Install the required packages from the requirements file using pip"

    with cd("%s" % env.path):
        run("pip install -E . -r ./releases/%s/requirements.txt" % release)

def symlink_shared_files():
    run("ln -s /srv/%s/shared/local_settings.py %s/current/project/local_settings.py" % (env.project_name, env.path))

def symlink_release(release):
    "Symlink our current release"

    with cd("%s" % env.path):
        run("ln -sfn ./releases/%s current" % release)


def setup_shared_directory():
    with cd("/srv/%s" % env.project_name):
        run("mkdir shared")


def create_logs_directories():
    run("mkdir %s" % env.log_path)
    run("mkdir %s/nginx" % env.log_path)
    run("mkdir %s/gunicorn" % env.log_path)
    run("mkdir %s/supervisor" % env.log_path)


def migrate():
    "Migrating the Database with South"
    run("%s/bin/python %s/current/manage.py migrate" % (env.path, env.path))


def clean_old_releases():
    if env.release_count <= 0:
        return

    with cd("%s/releases/" % env.path):
        folders = run("ls -A")
        folders = folders.split('\t')
        if len(folders) > env.release_count:
            count = len(folders) - env.release_count
            [run("rm -rf %s" % x) for x in folders[:count]]


def setup_configuration_files():
    run('mkdir /srv/%s/conf' % env.project_name)
    generate_gunicorn_script()
    generate_nginx_configuration()
    generate_supervisor_configuration()
    symlink_configuration_files()


def generate_gunicorn_script():
    gunicorn_sh = Loader().load_template('gunicorn.sh',
                                         template_dirs=[CONF_DIRECTORY])
    for line in gunicorn_sh.split("\n"):
        run("echo '%s' >> /srv/%s/conf/gunicorn.sh" % (line, env.project_name))


def generate_nginx_configuration():
    nginx_conf = Loader().load_template('nginx.conf',
                                        template_dirs=[CONF_DIRECTORY])
    for line in nginx_conf.split("\n"):
        run('echo %s >> /srv/%s/conf/nginx.conf'% (line, env.project_name))


def generate_supervisor_configuration():
    supervisor_conf = Loader().load_template('supervisor.conf',
                                             template_dirs=[CONF_DIRECTORY])
    for line in supervisor_conf.split("\n"):
        run("echo '%s' >> /srv/%s/conf/supervisor.conf" % (line, env.project_name))


def symlink_configuration_files():
    run('ln -sfn %s/conf/nginx.conf /etc/nginx/sites-enabled/%s.conf' %
        (env.path, env.project_name))
    run('ln -sfn %s/conf/supervisor.conf /etc/supervisor/conf.d/%s.conf' %
        (env.path, env.project_name))


def restart_nginx():
    run("service nginx restart")


def restart_gunicorn():
    "Restart Master gunicorn process"
    with settings(warn_only=True):  
        #attempt graceful restart
        pid = run('cat %s/../logs/gunicorn/gunicorn.pid' % env.path)
        if pid.succeeded:
            run('kill -HUP %s' %  pid)

        #could not get pid from file, must use supervisor
        else:
            run('supervisorctl restart %s' % env.project_name)
