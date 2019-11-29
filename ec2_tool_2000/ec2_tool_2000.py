import boto3
import botostubs
import botocore
import click
import sys
from datetime import datetime, timezone


ec2 = None  # type: botostubs.EC2.Ec2Resource


@click.group()
@click.option('--profile', default=None, help="Specify profile to use for AWS resource management. A 'default' profile is used as default")
def cli(profile):
    """A custom script to manage EC2 and EBS snapshots"""
    session = None
    if profile:
        try:
            session = boto3.Session(profile_name=profile)
            print("Using '{}' profile.".format(profile))
        except botocore.exceptions.ProfileNotFound as e:
            sys.exit("Unknown profile '{}'. ".format(profile) + str(e))
    else:
        session = boto3.Session(profile_name="default")
        print("Using 'default' profile.")

    global ec2
    ec2 = session.resource('ec2')
    return


"""
 ___ _  _ ___ _____ _   _  _  ___ ___ ___
|_ _| \| / __|_   _/_\ | \| |/ __| __/ __|
 | || .` \__ \ | |/ _ \| .` | (__| _|\__ \
|___|_|\_|___/ |_/_/ \_\_|\_|\___|___|___/
"""


@cli.group('instances')
def instances():
    """Commands for ec2 instances"""


@instances.command('list')
@click.option('--project', default=None, help="Only instances for project (tag Project:<name>)")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def list_instances(project, target_instance):
    "List EC2 instances"
    instances = filter_instances(project, target_instance)
    # print out all instances
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        tags = {t['Key']: t['Value'] for t in i.tags or []}
        print(", ".join((
            i.instance_id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name,
            tags.get('Project', '<no-project>')
        )))
    return


@instances.command('stop')
@click.option('--project', default=None, help="Only instances for project:<name>")
@click.option('--force', default=False, is_flag=True, help="Option to force action when the project or instance id is not specified")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def stop_instances(project, force, target_instance):
    "Stop EC2 instances"
    safeguard_action(project, target_instance, force)
    instances = filter_instances(project, target_instance)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        if not i.state['Name'] == 'stopped':
            try:
                print("Stopping {0}...".format(i.instance_id))
                i.stop()
            except botocore.exceptions.ClientError as e:
                print("Could not stop {}.".format(i.id) + str(e))
                continue
        else:
            print("Instance '{}' already in a stopped state".format(i.instance_id))
    return


@instances.command('start')
@click.option('--project', default=None, help="Only instances for project:<name>")
@click.option('--force', default=False, is_flag=True, help="Option to force action when the project or instance id is not specified")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def start_instances(project, force, target_instance):
    "Start EC2 instances"
    safeguard_action(project, target_instance, force)
    instances = filter_instances(project, target_instance)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        if not i.state["Name"] == "running":
            try:
                print("Starting {0}...".format(i.instance_id))
                i.start()
            except botocore.exceptions.ClientError as e:
                print("Could not start {}. ".format(i.id) + str(e))
                continue
        else:
            print("Instance '{}' is already in running state".format(i.instance_id))
    return


@instances.command('reboot')
@click.option('--project', default=None, help="Only instances for project:<name>")
@click.option('--force', default=False, is_flag=True, help="Option to force action when the project or instance id is not specified")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def reboot_instances(project, force, target_instance):
    "Reboot EC2 instances"
    safeguard_action(project, target_instance, force)
    instances = filter_instances(project, target_instance)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        if i.state['Name'] == 'running':
            print("Rebooting instance {}".format(i.instance_id))
            i.reboot()
        else:
            print("Reboot is only valid for instances in running state")


"""
__   _____  _   _   _ __  __ ___ ___
\ \ / / _ \| | | | | |  \/  | __/ __|
 \ V / (_) | |_| |_| | |\/| | _|\__ \
  \_/ \___/|____\___/|_|  |_|___|___/
"""


@cli.group('volumes')
def volumes():
    """ Commands for ebs volumes"""


@volumes.command('list')
@click.option('--project', default=None, help="Only volumes for project (tag Project:<name>)")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def list_volumes(project, target_instance):
    """Show EBS volumes"""
    instances = filter_instances(project, target_instance)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            print(", ".join((
                v.volume_id,
                i.instance_id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrypted"
            )))
    return


"""
 ___ _  _   _   ___  ___ _  _  ___ _____ ___
/ __| \| | /_\ | _ \/ __| || |/ _ \_   _/ __|
\__ \ .` |/ _ \|  _/\__ \ __ | (_) || | \__ \
|___/_|\_/_/ \_\_|  |___/_||_|\___/ |_| |___/

"""


@cli.group('snapshots')
def snapshots():
    """ Commands for ebs snapshots"""


@snapshots.command('list')
@click.option('--project', default=None, help="Only snapshots for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True, help="Option to show all snapshots instead of only the latest")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def list_snapshots(project, list_all, target_instance):
    """Show EBS snapshots"""
    instances = filter_instances(project, target_instance)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            s: botostubs.EC2.Ec2Resource.Snapshot
            for s in v.snapshots.all():
                print(", ".join((
                    s.snapshot_id,
                    v.volume_id,
                    i.instance_id,
                    s.description,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c"),
                )))

                if s.state == 'completed' and not list_all:
                    break
    return


@snapshots.command('create')
@click.option('--project', default=None, help="Only snapshots for project (tag Project:<name>)")
@click.option('--force', default=False, is_flag=True, help="Option to force action when the project or instance id is not specified")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
@click.option('--age', default=None, help="Create snapshot of volumes with last snapshot older than 'age' days")
def create_snapshots(project, force, target_instance, age):
    """Create EBS snapshots"""
    safeguard_action(project, target_instance, force)
    instances = filter_instances(project, target_instance)
    running_instances = set()
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            time_now = datetime.now(timezone.utc)
            last_volume_snapshot_time = get_last_snapshot(v)
            volume_snapshot_age = time_now - last_volume_snapshot_time
            if volume_snapshot_age.days >= int(age):
                if has_pending_snapshot(v):
                    print("Skipping: volume {} has a pending snapshot".format(
                        v.volume_id))
                else:
                    try:
                        if i.state["Name"] == "running":
                            running_instances.add(i)
                            print("Stopping EC2 instance: {}".format(
                                i.instance_id))
                            i.stop()
                            i.wait_until_stopped()
                        print("Creating snapshot for instance:{} ...".format(
                            v.volume_id))
                        v.create_snapshot(
                            Description="Script generated snapshot")
                    except botocore.exceptions.ClientError as e:
                        print("Could not create a snapshot for volume: {}. ".format(
                            v.volume_id) + str(e))
            else:
                print("Skipping: A snapshot of volume '{}' has been created in the last '{}' days".format(
                    v.volume_id, age))

    for i in running_instances:
        print("Re-starting EC2 instance '{}'".format(i.instance_id))
        i.start()

    return


@snapshots.command('delete')
@click.option('--project', default=None, help="Only snapshots for project (tag Project:<name>)")
@click.option('--force', default=False, is_flag=True, help="Option to force action when the project or instance id is not specified")
@click.option('--instance', 'target_instance', default=None, help="Only specified instance")
def delete_snapshots(project, force, target_instance):
    """Delete EBS snapshots"""
    safeguard_action(project, target_instance, force)
    instances = filter_instances(project, target_instance)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            s: botostubs.EC2.Ec2Resource.Snapshot
            for s in v.snapshots.all():
                print("Delete snapshot for instance:{} ...".format(v.volume_id))
                s.delete()
    return


"""
 _   _ _____ ___ _    ___
| | | |_   _|_ _| |  / __|
| |_| | | |  | || |__\__ \
 \___/  |_| |___|____|___/

"""


def filter_instances(project, target_instance):
    instances = []
    if not project and not target_instance:
        instances = ec2.instances.all()
    elif project and target_instance:
        filters = [{'Name': 'tag:Project', 'Values': [project]}]
        instances = ec2.instances.filter(Filters=filters)
        instances = instances.filter(InstanceIds=[target_instance])
    else:
        if target_instance:
            instances = ec2.instances.filter(InstanceIds=[target_instance])
        if project:
            filters = [{'Name': 'tag:Project', 'Values': [project]}]
            instances = ec2.instances.filter(Filters=filters)
    return instances


def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'


def get_last_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    if snapshots:
        return snapshots[0].start_time


def safeguard_action(project, target_instance, force):
    if not project and not target_instance and not force:
        sys.exit("Operation denied. Please specify project or use --force flag")


"""
 __  __      _
|  \/  |__ _(_)_ _
| |\/| / _` | | ' \
|_|  |_\__,_|_|_||_|
"""

if __name__ == "__main__":
    cli()
