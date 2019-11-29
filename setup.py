from setuptools import setup

setup(
    name='ec2_tool_2000',
    version='0.3',
    author="Samuel O. Idowu",
    author_email="samup4web@yahoo.com",
    description="EC2_tool_2000 is a tool to manage EC2 resources",
    license="GPLv3+",
    packages=['ec2_tool_2000'],
    url="https://github.com/samup4web/ec2_tools-2000",
    install_requires=[
        'click',
        'boto3',
        'botostubs'
    ],
    entry_points= {
        'console_scripts': [
            'ec2_tool = ec2_tool_2000.ec2_tool_2000:cli'
        ],
    }
)