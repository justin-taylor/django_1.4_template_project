from fabric.api import env

env.hosts = ['107.20.88.55']
env.virtualenv_name = 'application'
env.path = '/srv/%s/%s' % (env.project_name, env.virtualenv_name)
env.user = 'root'
env.log_path = '/srv/%s/logs' % env.project_name

env.gunicorn_port = 8001
env.gunicorn_worker_count = 3
env.gunicorn_user = 'root'
env.gunicorn_group = 'root'

env.supervisor_user = env.gunicorn_user

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


