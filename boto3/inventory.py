import boto3


REGION = "eu-west-2"


def list_ec2_instances(ec2):
    paginator = ec2.get_paginator("describe_instances")
    count = 0

    print("\nEC2 INSTANCES")
    print("-" * 60)

    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                count += 1

                print(
                    f"Instance ID: {instance['InstanceId']} | "
                    f"State: {instance['State']['Name']} | "
                    f"Type: {instance['InstanceType']}"
                )

    if count == 0:
        print("No EC2 instances found.")

    print(f"Total EC2 instances: {count}")


def list_ebs_volumes(ec2):
    paginator = ec2.get_paginator("describe_volumes")
    count = 0

    print("\nEBS VOLUMES")
    print("-" * 60)

    for page in paginator.paginate():
        for volume in page.get("Volumes", []):
            count += 1

            print(
                f"Volume ID: {volume['VolumeId']} | "
                f"State: {volume['State']} | "
                f"Size: {volume['Size']} GiB | "
                f"Type: {volume['VolumeType']}"
            )

    if count == 0:
        print("No EBS volumes found.")

    print(f"Total EBS volumes: {count}")


def list_elastic_ips(ec2):
    response = ec2.describe_addresses()
    addresses = response.get("Addresses", [])

    print("\nELASTIC IPS")
    print("-" * 60)

    if not addresses:
        print("No Elastic IPs found.")

    for address in addresses:
        print(
            f"Public IP: {address.get('PublicIp')} | "
            f"Instance ID: {address.get('InstanceId', 'Not attached')} | "
            f"Association ID: "
            f"{address.get('AssociationId', 'Not associated')}"
        )

    print(f"Total Elastic IPs: {len(addresses)}")


def list_rds_instances(rds):
    paginator = rds.get_paginator("describe_db_instances")
    count = 0

    print("\nRDS DATABASES")
    print("-" * 60)

    for page in paginator.paginate():
        for database in page.get("DBInstances", []):
            count += 1

            print(
                f"Database: {database['DBInstanceIdentifier']} | "
                f"Status: {database['DBInstanceStatus']} | "
                f"Engine: {database['Engine']} | "
                f"Class: {database['DBInstanceClass']}"
            )

    if count == 0:
        print("No RDS databases found.")

    print(f"Total RDS databases: {count}")


def list_load_balancers(elbv2):
    paginator = elbv2.get_paginator("describe_load_balancers")
    count = 0

    print("\nLOAD BALANCERS")
    print("-" * 60)

    for page in paginator.paginate():
        for load_balancer in page.get("LoadBalancers", []):
            count += 1

            print(
                f"Name: {load_balancer['LoadBalancerName']} | "
                f"Type: {load_balancer['Type']} | "
                f"Scheme: {load_balancer['Scheme']} | "
                f"State: {load_balancer['State']['Code']}"
            )

    if count == 0:
        print("No load balancers found.")

    print(f"Total load balancers: {count}")


def list_lambda_functions(lambda_client):
    paginator = lambda_client.get_paginator("list_functions")
    count = 0

    print("\nLAMBDA FUNCTIONS")
    print("-" * 60)

    for page in paginator.paginate():
        for function in page.get("Functions", []):
            count += 1

            print(
                f"Function: {function['FunctionName']} | "
                f"Runtime: {function.get('Runtime', 'Not specified')} | "
                f"Memory: {function['MemorySize']} MB | "
                f"Timeout: {function['Timeout']} seconds"
            )

    if count == 0:
        print("No Lambda functions found.")

    print(f"Total Lambda functions: {count}")


def list_eks_clusters(eks):
    paginator = eks.get_paginator("list_clusters")
    count = 0

    print("\nEKS CLUSTERS")
    print("-" * 60)

    for page in paginator.paginate():
        for cluster_name in page.get("clusters", []):
            count += 1

            response = eks.describe_cluster(name=cluster_name)
            cluster = response["cluster"]

            print(
                f"Cluster: {cluster['name']} | "
                f"Status: {cluster['status']} | "
                f"Version: {cluster['version']}"
            )

    if count == 0:
        print("No EKS clusters found.")

    print(f"Total EKS clusters: {count}")


def list_ecr_repositories(ecr):
    paginator = ecr.get_paginator("describe_repositories")
    count = 0

    print("\nECR REPOSITORIES")
    print("-" * 60)

    for page in paginator.paginate():
        for repository in page.get("repositories", []):
            count += 1

            print(
                f"Repository: {repository['repositoryName']} | "
                f"URI: {repository['repositoryUri']} | "
                f"Tag mutability: {repository['imageTagMutability']}"
            )

    if count == 0:
        print("No ECR repositories found.")

    print(f"Total ECR repositories: {count}")


def main():
    print(f"Scanning AWS resources in region: {REGION}")

    ec2 = boto3.client("ec2", region_name=REGION)
    rds = boto3.client("rds", region_name=REGION)
    elbv2 = boto3.client("elbv2", region_name=REGION)
    lambda_client = boto3.client("lambda", region_name=REGION)
    eks = boto3.client("eks", region_name=REGION)
    ecr = boto3.client("ecr", region_name=REGION)

    list_ec2_instances(ec2)
    list_ebs_volumes(ec2)
    list_elastic_ips(ec2)
    list_rds_instances(rds)
    list_load_balancers(elbv2)
    list_lambda_functions(lambda_client)
    list_eks_clusters(eks)
    list_ecr_repositories(ecr)


if __name__ == "__main__":
    main()