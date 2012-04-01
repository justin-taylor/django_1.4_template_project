from __future__ import with_statement
from fabric.api import run, sudo, env, local, require, cd

# globals


'''
setup to use gunicorn and nginx
supervisorctl restart example
'''

env.project_name = 'example'

# environments

def production():
    env.hosts = ['107.20.88.55']
    env.path = '/srv/example.com'
    env.user = 'root'
    env.git_repo = 'git://github.com/justin-taylor/test_app.git'
    import time
    env.release = time.strftime('%Y%m%d%H%M%S')

# tasks
def test():
    "Run the test suite and bail out if it fails"
    local("cd $(project_name); python manage.py test", fail="abort")

def deploy():
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules, 
    then restart the webserver
    """
    clone_release()
    install_requirements()
    symlink_current_release()
    migrate()
    restart_webserver()

#TODO
def deploy_version(version):
    pass

#TODO
def rollback():
    pass


# Helpers. These are called by other functions rather than directly

def clone_release():
    require('path', provided_by=[production])
    require('release', provided_by=[deploy])
    require('git_repo', provided_by=[production])

    with cd("%s/releases/" % env.path):
        sudo("git clone %s %s" % (env.git_repo, env.release))

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('path', provided_by=[production])
    require('release', provided_by=[deploy])

    with cd("%s" % (env.path)):
        sudo("pip install -r ./releases/%s/requirements.txt" % (env.release))

def symlink_current_release():
    "Symlink our current release"
    require('path', provided_by=[production])
    require('release', provided_by=[deploy])

    with cd("%s;" % (env.path)):
        sudo("ln -sfn %s releases/current" % (env.release))

def migrate():
    "Migrating the Database with South"
    require('project_name')
    require('path', provided_by=[production])

    with cd("%s/releases/current/;" % (env.path)):
        sudo("./manage.py migrate")

def restart_webserver():
    "Restart the web server"
    require('project_name')
    sudo('supervisorctl restart %s' % (env.project_name))
