from __future__ import with_statement
from fabric.api import run, env, local, cd
from fabric.context_managers import settings

env.project_name = 'central.tayloredapps.org'

# the number of releases to keep in the release folder
# before deleting old releases
# set to a negative number or zero to turn this feature off
env.release_count = 5

#-------------------------------------------------------------------------------
#    ENVIRONMENTS
#-------------------------------------------------------------------------------

def production():
    env.hosts = ['107.20.88.55']
    env.virtualenv_name = 'application'
    env.path = '/srv/%s/%s' % (env.project_name, env.virtualenv_name)
    env.user = 'root'

    env.conf_repo = 'git://github.com/justin-taylor/server_conf.git'

    env.git_repo = 'git://github.com/justin-taylor/central.git'
    env.git_branch = 'master'

    env.apt_get_dependencies = (
        'git',
        'mysql-server',
        'nginx',
        'supervisor',
        'python-pip',
        'build-dep',
        'python-mysqldb',
    )

    env.pip_dependencies = (
        'virtualenv',
    )

    import time
    env.release = time.strftime('%Y%m%d%H%M%S')

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
        symlink_current_release(release)
        install_requirements(release)
        migrate()
        restart_webserver()

    except:
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


#TODO
def setup():
    """
    runs the initial setup of the django project
    """

    run("cd /srv && mkdir %s" % env.project_name)
    with cd("/srv/%s" % env.project_name):
        run("virtualenv %s" % env.virtualenv_name)
        run("mkdir %s/releases" % env.virtualenv_name)
        run("mkdir logs")
        run("mkdir logs/nginx")
        run("mkdir logs/supervisor")
        run("git clone %s conf" % env.conf_repo)

    clone_release()

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

        symlink_current_release(folders[0])
        install_requirements(folders[0])
        restart_webserver()

        if delete != 'no_delete':
            run("rm -r %s" % folders[1])


#-------------------------------------------------------------------------------
# HELPER METHODS
#-------------------------------------------------------------------------------

def clone_release():
    with cd("%s/releases/" % env.path):
        run("git clone -b %s %s %s" % (env.git_branch, env.git_repo, env.release))

def install_requirements(release):
    "Install the required packages from the requirements file using pip"

    with cd("%s" % env.path):
        run("pip install -E . -r ./releases/%s/requirements.txt" % release)

def symlink_current_release(release):
    "Symlink our current release"

    with cd("%s" % env.path):
        run("ln -sfn ./releases/%s current" % release)

def migrate():
    "Migrating the Database with South"

    with cd("%s/current/" % env.path):
        run("%s/bin/python manage.py migrate" % env.path)

def clean_old_releases():
    if env.release_count <= 0:
        return

    with cd("%s/releases/" % env.path):
        folders = run("ls -A")
        folders = folders.split('\t')
        if len(folders) > env.release_count:
            count = len(folders) - env.release_count
            [run("rm -rf %s" % x) for x in folders[:count]]

def restart_webserver():
    "Restart Master gunicorn process"
    with settings(warn_only=True):  
        #attempt graceful restart
        pid = run('cat %s/../gunicorn.pid' % env.path)
        if pid.succeeded:
            run('kill -HUP %s' %  pid)

        #could not get pid from file, must use supervisor
        else:
            run('supervisorctl restart %s' % env.project_name)
