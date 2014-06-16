#!/usr/bin/env python

import subprocess, os, sys, uuid, re, getpass
try:
  from termcolor import colored
except ImportError:
  print '`sudo pip install termcolor` to get this deployer script in color!'
  def colored(msg, color, **kwargs):
    return msg
try:
  import requests
except ImportError:
  sys.exit('`sudo pip install requests` is required to continue!')

def open_or_print(url):
  print colored(url, 'cyan')
  if prompt_get_yes_no('Open this url in your browser'):
    for command in ['open', 'xdg-open', 'start']:
      if call_without_output([command, url]) == 0:
        return

def call_without_output(cmd):
  return subprocess.call(cmd, stdout=DEVNULL, stderr=DEVNULL)

def prompt(instructions):
  return raw_input(colored(instructions + ": ", 'blue', attrs=['bold']))

def prompt_password(instructions):
  return getpass.getpass(colored(instructions + ": ", 'blue', attrs=['bold']))

def clear():
  subprocess.call('cls' if os.name == 'nt' else 'clear')

def get_json(url, auth=None):
  headers = {'User-Agent': 'github-s3-auth-deployer'}
  response = requests.get(url, headers=headers, auth=auth)
  if response.headers.get('X-GitHub-OTP'):
    code = prompt('Your GitHub 2-Factor Authentication Code')
    headers['X-GitHub-OTP'] = code
    response = requests.get(url, headers=headers, auth=auth)
  return response.json()

def check_for_heroku():
  if call_without_output(['which', 'heroku']) != 0:
    print colored('Please install and set up the Heroku Toolbelt before running this script!', 'red')
    open_or_print('https://toolbelt.heroku.com/')
    sys.exit()
  print colored('Checking your Heroku credentials...', 'magenta')
  subprocess.call(['heroku', 'auth:whoami'])
  print
  print colored('Welcome to the github-s3-auth deployer script!', 'green')

def prompt_with_condition(message, condition, error):
  done = False
  while not done:
    inp = prompt(message)
    if not condition(inp):
      print colored(error, 'red')
    else:
      done = True
  return inp

def prompt_need_response(var):
  return prompt_with_condition(var, lambda x: len(x) > 0, 'you must enter a {}'.format(var))

def prompt_with_length(var, length):
  return prompt_with_condition(var, lambda x: len(x) == length, '{} must be {} characters long'.format(var, length))

def prompt_get_yes_no(prompt):
  return prompt_need_response('{}? [y/n]'.format(prompt)).lower() == 'y'

def get_gh_auth():
  GH_USER = prompt_need_response('Your GitHub Username')
  GH_PASSWORD = prompt_password('Your GitHub Password')
  return (GH_USER, GH_PASSWORD)

def params_dict(_locals):
  params = ['APP_NAME', 'SK', 'AWS_BUCKET', 'AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'GH_ORG', 'GH_REPO', 'GH_ORG_NAME', 'GH_REPO_NAME', 'GH_CLIENT_ID', 'GH_SECRET']
  return {param:_locals.get(param) for param in params}

def get_params():
  env_params = params_dict(locals())
  if None not in env_params.values():
    if prompt_get_yes_no('Use current environment variables'):
      return env_params

  print colored('Please enter the following config vars.', 'green')
  print
  APP_NAME = prompt('Heroku App Name (blank for random)') or ''
  SK = prompt('Flask App Secret Key (blank for random)') or str(uuid.uuid4())

  AWS_BUCKET = prompt_need_response('S3 Bucket Name')
  AWS_ACCESS_KEY = prompt_with_length('AWS Access Key', 20)
  AWS_SECRET_KEY = prompt_with_length('AWD Secret Key', 40)

  GH_ORG_NAME = prompt_need_response('Name of GitHub Org to Validate (Case-Sensitive)')
  GH_REPO_NAME = prompt_need_response('Name of GitHub Repo to Validate (Case-Sensitive)')

  print colored('Trying to fetch your org id from the GitHub API', 'magenta')
  try:
    GH_ORG = get_json('https://api.github.com/orgs/{}'.format(GH_ORG_NAME))['id']
    print colored('Found an org with id of {}!'.format(GH_ORG), 'grey')
  except:
    print colored('Could not automatically find that GitHub Organization!', 'red')
    print colored('Use the GitHub API to get your org id', 'green')
    open_or_print('https://developer.github.com/v3')
    GH_ORG = prompt_with_condition('GitHub Org Id', lambda x: x.isdigit() ,'org id must be an int')
 
  print colored('Trying to fetch your repo id from the GitHub API', 'magenta')
  try:
    repos = get_json('https://api.github.com/orgs/{}/repos'.format(GH_ORG_NAME), auth=get_gh_auth())
    for repo in repos:
      if repo['name'] == GH_REPO_NAME:
        GH_REPO = repo['id']
    print colored('Found an repo with id of {}!'.format(GH_REPO), 'grey')
  except:
    raise
    print colored('Could not automatically find that GitHub Repo!', 'red')
    print colored('Use the GitHub API to get your org id', 'green')
    open_or_print('https://developer.github.com/v3')
    GH_REPO = prompt_with_condition('GitHub Repo Id', lambda x: x.isdigit() ,'org id must be an int')

  print colored('You must now create a new GitHub App to authenticate users', 'green')
  open_or_print('https://github.com/organizations/{}/settings/applications/new'.format(GH_ORG_NAME))
  print colored('Enter an Application Name, and anything as the Homepage URL (for now)', 'green')
  print colored("Click 'Register Application'", 'green')

  GH_CLIENT_ID = prompt_with_length('GitHub Client Id', 20)
  GH_SECRET = prompt_with_length('GitHub Client Secret', 40)
  
  _locals = locals()
  return params_dict(_locals)

def deploy(params):
  print colored('Creating Heroku App', 'magenta')
  try:
    if params['APP_NAME']:
      output = subprocess.check_output(['heroku', 'create', params['APP_NAME']])
    else:
      output = subprocess.check_output(['heroku', 'create'])
    params['APP_NAME'] = re.match(r'Creating (.*)\.\.\.', output).group(1)
  except subprocess.CalledProcessError:
    sys.exit(colored('Heroku app creation failed!', 'red'))
  config = map(lambda x: "{}={}".format(x[0], x[1]), params.items())

  print colored('Writing Heroku Config Vars To .env', 'magenta')
  with open('.env', 'w') as f:
    f.write("\n".join(config))

  print colored('Setting Heroku Config Vars', 'magenta')
  call_without_output(['heroku', 'config:set'] + config + ['--app', params['APP_NAME']])

  print colored('Deploying to Heroku', 'magenta')
  git_remote = 'git@heroku.com:{}.git'.format(params['APP_NAME'])
  call_without_output(['git', 'remote', 'add', params['APP_NAME'], git_remote])
  call_without_output(['git', 'push', params['APP_NAME'], 'master'])

  colored("You need to update your GitHub App", 'green')
  open_or_print('https://github.com/organizations/{}/settings/applications'.format(GH_ORG_NAME))

  message = colored("Set your GitHub App's Homepage URL to ", 'green') \
  + colored("http://{}.herokuapp.com".format(params['APP_NAME']), 'cyan')
  print message
  prompt_with_condition('done? [y/n]', lambda x: x.lower() == 'y', message)

  message = colored("Set your GitHub App's Authorization Callback URL to ", 'green') \
  + colored("http://{}.herokuapp.com/callback".format(params['APP_NAME']), 'cyan')
  print message
  prompt_with_condition('done? [y/n]', lambda x: x.lower() == 'y', message)

  print colored("Save your settings by clicking 'Update Application'", 'green')

  print colored('Launching App!', 'magenta')
  call_without_output(['heroku', 'ps:scale', 'web=1'])
  call_without_output(['heroku', 'apps:open', '--app', params['APP_NAME']])

  print colored('App URL: ', 'green') \
  + colored('http://{}.herokuapp.com'.format(params['APP_NAME']), 'cyan')

if __name__ == '__main__':
  DEVNULL = open(os.devnull, 'w')
  try:
    clear()
    check_for_heroku()
    params = get_params()
    deploy(params)
  except KeyboardInterrupt:
    sys.exit(colored('\nDeploy cancelled', 'red'))