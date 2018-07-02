import requests
import os
from sys import argv,exit
import logging
import yaml

######## Settings #############################################################################################>

URL = "http://<URL>"
TOKEN = os.getenv('ART_TOKEN')
SETTINGS = './test.yaml'
REPO_TYPES = {"pypi", "docker", "generic", "rpm"}

#### Logger ####
FORMAT = '%(asctime)s %(funcName)s %(levelname)s:   %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)


######## Settings #############################################################################################<

class ACREATOR():
    def __init__(self, token):
        self.token = token
        self.headers = {'X-JFrog-Art-Api' : TOKEN}


########## Checks #############################################################################################>

    def test(self, users=""):
        return self.__user_check(users)

    # Checking if repos exists (rclass *str, repo_name *str), returns HTTP response code *int
    def __rcheck(self, rclass, repo_name):
        self.repo_name = repo_name
        url = URL + 'repositories/' + repo_name
        req = requests.get(url=url, headers=self.headers)
        return req.status_code

    # Checking if users exists (users *tuple), returns valid users hash {user:parameters}
    def __user_check(self, users=""):
        valid_users = {}
        for user in users:
            url = URL + 'security/users/' + user
            req = requests.get(url=url, headers=self.headers)
            if req.status_code == 200:
                valid_users.update({user:dict(req.json())})
            else:
                logging.warning(user + " doesn't exists !")
        return valid_users

    # Checking if group exists (group *str), returns HTTP response code *int
    def __group_check(self, group=""):
        self.group = group
        url = URL + 'security/groups/' + self.group
        req = requests.get(url=url, headers=self.headers)
        return req.status_code

    # Checking if permissions exists (group *str), returns HTTP response code *int
    def __perm_check(self, perm=""):
        url = URL + 'security/permissions/' + perm
        req = requests.get(url=url, headers=self.headers)
        return req.status_code

########## Checks end #############################################################################################<
    
    # Creating repo after unless check has been done. Returns response text *str
    def repo_create(self,repo_name, rclass="local", rtype="rpm", rdesk="", rnotes=""):
        if self.__rcheck(rclass,repo_name) == 200:
            logging.warning("Repo " + repo_name + " already exists !")
            exit(0)
        elif rtype not in REPO_TYPES:
            logging.error("Wrong repository type !")
        else:
            data = {'key':repo_name, 'rclass':rclass, 'packageType':rtype, 'description':rdesk, 'notes':rnotes, 'propertySets':["artifactory"]}
            url = URL + 'repositories/' + repo_name
            req = requests.put(url=url, headers=self.headers, json=data)
            if req.status_code == 200:
                logging.info("Repo " + repo_name + " is created !")
            else:
                logging.error('%s', req.text)
            return req.text

    def user_assign(self, users):
        for user, value in self.__user_check(users).items():
            value['groups'].append(self.group)
            logging.debug('Checking valid_users status ' + user)
            data = value
            url = URL + 'security/users/' + user
            logging.debug('%s', value)
            req = requests.post(url=url, headers=self.headers, json=data)
            if req.status_code == 200:
                logging.info(user + " added to " + self.group)
            else:
                logging.error("Some problems with " + user)
                logging.error('%s', req.text)
        return True

    def group_create(self, group=""):
        if self.__group_check(group) == 200:
            logging.warning("Group " + group + " already exists !")
            exit(0)
        else:
            url = URL + 'security/groups/' + self.group
            data = {'name':self.group, 'description':"", 'realm':"ARTIFACTORY"}
            req = requests.put(url=url, headers=self.headers, json=data)
            if req.status_code in (200, 201):
                logging.info("Group " + group + " is created !")
                return group
            else:
                logging.debug("Can't create a group " + str(data))
                logging.error('%s', req.text)
                exit(1)

    def perm_create(self, perm):
        if self.__perm_check(perm) == 200:
            logging.warning(perm + " permission already exists")
            exit(0)
        else:
            try:
                isinstance(self.repo_name, str)
            except TypeError:
                print("Wrong variable type:" + self.repo_name)
                exit(1)
            data = {'name':perm, 'repositories': [self.repo_name], 'principals' : {'groups' : {self.group : [ "r", "d", "w", "n" ]}}}
            url = URL + 'security/permissions/' + perm
            logging.debug('%s', data)
            req = requests.put(url=url, headers=self.headers, json=data)
            if req.status_code in (200, 201):
                logging.info("Permission is created " + perm)
                return perm
            else:
                logging.debug("Can't create a premission " + str(data))
                logging.error('%s', req.text)
                exit(1)

    def __token_getter(self, username):
            url = URL + 'security/token'
            headers = self.headers
            headers.update({'Content-Type': 'application/x-www-form-urlencoded'})
            data = {'username':self.ci_user}
            req = requests.post(url=url, headers=headers, data=data)
            if req.status_code in (200,201):
                return req.text
            else:
                logging.error("Can't generate a token for " + self.ci_user)
                logging.debug('%s', req.text)
                return False

    def ci_user_create(self):
            self.ci_user = self.repo_name + "-ci"
            url = URL + 'security/users/' + self.ci_user
            data = {'name':self.ci_user, "email":"devnull@devnull.ru", 'disableUIAccess': True, 'internalPasswordDisabled': True, 'groups': [self.group]}
            req = requests.put(url=url, headers=self.headers, json=data)
            if req.status_code in (200, 201):
                logging.info("CI user " + self.ci_user + " is created !")
                token = {self.ci_user: self.__token_getter(self.ci_user)}
                logging.info('%s', token)
                return token
            else:
                logging.debug("Can't create CI user" + str(data))
                logging.error('%s', req.text)
                exit(1)

###############################################################################################################<

################################# User functions ##############################################################>

def create_local_repo(repo_name, users, responsible="", ticket_id="", rtype="rpm", ci=False):
    try:
        isinstance(users, tuple)
        isinstance(repo_name, str)
    except TypeError:
        print("Wrong variable type !")

    new = ACREATOR(TOKEN)
    new.repo_create(repo_name=repo_name, rdesk="Responsible: "+responsible, rnotes=ticket_id, rtype=rtype)
    new.group_create(group=repo_name)
    new.perm_create(perm=repo_name)
    new.user_assign(users=users)
    if ci == True:
        new.ci_user_create()
    return True

# returns dict
def settings_loader(settings_path="settings.yaml"):
    with open(settings_path) as settings:
        repos = yaml.safe_load(settings)
    return repos

################################# User functions ##############################################################<


if __name__ == "__main__":

    try:
        repo = settings_loader()
        repo_id = next(iter(repo))
        repo_val = repo[repo_id]
    except IOError:
        logging.error("Can't open settings file")

    create_local_repo(repo_name=repo_id, users=repo_val['participants'], responsible=repo_val['responsible'], ticket_id=repo_val['ticket_id'], rtype=repo_val['repo_type'], ci=True)
