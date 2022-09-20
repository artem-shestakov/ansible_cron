import os
import re
import yaml
import testinfra.utils.ansible_runner

# testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
#     os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

def get_vars(path: str):
    """
    Get dict from yml file
    """
    with open(path) as var_file:
        vars = yaml.load(var_file, yaml.Loader)
        return vars

def get_cron_jobs(vars: dict):
    """
    Get cron jobs from cron_jobs variable
    and generate lists of this jobs in cron format
    """
    cron_jobs = []
    for job in vars["cron_jobs"]:
        cron_job = ""
        for template_index in ["minute", "hour", "day", "month", "weekday"]:
            if template_index in job:
                cron_job += job[template_index] + " "
            else:
                cron_job += "* "
        cron_job += job["job"]
        cron_jobs.append(cron_job)
    return cron_jobs

def path_env(path: str, host):
    # Get env variable from path
    env_var = re.search(r"(^|.*)\/?(\$[\w]*)(\/?)", path).group(2)[1:]

    # Replace environment by value in path
    # use [:-1] to delete \n in echo stdout
    path = re.sub(r"(^|.*)\/?(\$[\w]*)(\/?)", host.run(f"echo ${env_var}").stdout[:-1] + "/", path)
    return path
        
def test_cron_unit(host):
    """
    Test cron unit installed and running
    """
    if host.system_info.distribution == "debian" or host.system_info.distribution == "ubuntu":
        cron = host.service("cron")
    elif host.system_info.distribution == "redhat":
        cron = host.service("crond")
    else:
        assert False
    assert cron.is_running
    assert cron.is_enabled

def test_cron_jobs(host):
    """
    Parse cron jobs from variables
    Check if jobs exists in host's cron jobs
    """
    sys_cron_jobs = host.run("crontab -l").stdout
    var_cron_jobs = get_cron_jobs(get_vars("./molecule/default/host_vars/instance.yml"))
    for job in var_cron_jobs:
        if job in sys_cron_jobs:
            assert True
        else:
            assert False

def test_cron_script(host):
    """
    Parse cron jobs from variables
    Check if jobs script exists on host
    """
    cron_jobs = get_vars("./molecule/default/host_vars/instance.yml")["cron_jobs"]
    for job in cron_jobs:
        if "file" in job:
            path = path_env(job["file"]["dest"], host)
            assert host.file(path).exists
            assert host.file(path).is_file
            assert oct(host.file(path).mode) == '0o700'
