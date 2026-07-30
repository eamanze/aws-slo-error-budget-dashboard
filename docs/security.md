# Security model

- Only the ALB accepts public ingress; ECS tasks accept port 8080 only from the ALB security group.
- No SSH port, static AWS keys, or secrets are committed.
- Containers run as UID 10001 with a read-only root filesystem and no Linux capabilities locally.
- CloudWatch log groups use KMS-compatible server-side encryption and explicit retention.
- ECR image scanning and immutable tags are enabled.
- CI runs dependency, filesystem, container, and Terraform checks.

For a public deployment, supply an ACM certificate, attach AWS WAF, store the fault token in Secrets Manager/Parameter Store, disable fault endpoints in normal operation, and use a restricted remote Terraform state backend with locking.

