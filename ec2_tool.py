import boto3, botostubs
import botocore
import click

session = boto3.Session(profile_name="aws_cli_admin")
ec2 = session.resource('ec2') #type: botostubs.EC2.Ec2Resource


@click.group()
def cli():
    """A custom script to manage EC2 and EBS snapshots"""

"""INSTANCES"""

@cli.group('instances')
def instances():
    """Commands for ec2 instances"""

@instances.command('list')
@click.option('--project', default=None, help="Only instances for project (tag Project:<name>)")
def list_instances(project):
    "List EC2 instances"
    instances = filter_instances(project)
    # print out all instances
    for i in instances: #type: botostubs.EC2.Ec2Resource.Instance
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
def stop_instances(project):
    "Stop EC2 instances"
    instances = filter_instances(project)

    for i in instances: #type: botostubs.EC2.Ec2Resource
        print("Stopping {0}...".format(i.instance_id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not stop {}.".format(i.id) + str(e))
            continue
    return


@instances.command('start')
@click.option('--project', default=None, help="Only instances for project:<name>")
def start_instances(project):
    "Start EC2 instances"
    instances = filter_instances(project)
    for i in instances:  #type: botostubs.EC2.Ec2Resource
        print("Starting {0}...".format(i.instance_id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not start {}. ".format(i.id) + str(e))
            continue
    return


"""VOLUMES"""

@cli.group('volumes')
def volumes():
    """ Commands for ebs volumes"""

@volumes.command('list')
@click.option('--project', default=None, help="Only volumes for project (tag Project:<name>)")
def list_volumes(project):
    """Show EBS volumes"""
    instances = filter_instances(project)
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

"""SNAPSHOTS"""

@cli.group('snapshots')
def snapshots():
    """ Commands for ebs snapshots"""

@snapshots.command('list')
@click.option('--project', default=None, help="Only snapshots for project (tag Project:<name>)")
def list_snapshots(project):
    """Show EBS snapshots"""
    instances = filter_instances(project)
    for i in instances:
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            s: botostubs.EC2.Ec2Resource.Snapshot
            for s in v.snapshots.all():
                print(", ".join((
                    s.snapshot_id,
                    s.description,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c"),
                )))
    return

@snapshots.command('create')
@click.option('--project', default=None, help="Only snapshots for project (tag Project:<name>)")
def create_snapshots(project):
    """Create EBS snapshots"""
    instances = filter_instances(project)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        print("Stopping EC2 instance: {}".format(i.instance_id))
        i.stop()
        i.wait_until_stopped()
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            print("Creating snapshot for instance:{} ...".format(v.volume_id))
            v.create_snapshot(Description="Script generated snapshot")
    return


@snapshots.command('delete')
@click.option('--project', default=None, help="Only snapshots for project (tag Project:<name>)")
def delete_snapshots(project):
    """Delete EBS snapshots"""
    instances = filter_instances(project)
    i: botostubs.EC2.Ec2Resource.Instance
    for i in instances:
        v: botostubs.EC2.Ec2Resource.Volume
        for v in i.volumes.all():
            s: botostubs.EC2.Ec2Resource.Snapshot
            for s in v.snapshots.all():
                print("Delete snapshot for instance:{} ...".format(v.volume_id))
                s.delete()
    return



#helper-functions
def filter_instances(project):
    instances = []
    if project:
        filters = [{'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()
    return instances


# main
if __name__ == "__main__":
    cli()
