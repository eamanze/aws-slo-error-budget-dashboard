# AWS deployment

The Terraform stack creates an ALB across two public subnets and an ECS/Fargate service across two private subnets. It also creates ECR, autoscaling, CloudWatch logging/alarming, and an AWS Budget. There is no SSH access.

## State bootstrap

For a team deployment, create a versioned, encrypted S3 state bucket and lock table outside this stack, then add an `s3` backend block to `versions.tf`. Local state is suitable only for evaluation and must never be committed.

## Deploy

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
terraform -chdir=terraform init
terraform -chdir=terraform plan -out=tfplan
terraform -chdir=terraform apply tfplan
```

Use an image digest for `container_image`. Supply an ACM certificate to redirect HTTP to HTTPS. Review the plan and the cost note before applying.

## Cost note

The NAT gateway, ALB, and two continuously running Fargate tasks incur charges. The exact amount varies by region and traffic. AWS Budget warns about spend but does not stop resources. Destroy lab infrastructure when finished:

```bash
terraform -chdir=terraform destroy
```

