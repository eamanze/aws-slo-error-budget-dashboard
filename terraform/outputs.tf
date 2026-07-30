output "application_url" {
  description = "Public application URL."
  value       = "${var.certificate_arn == null ? "http" : "https"}://${aws_lb.app.dns_name}"
}

output "ecr_repository_url" {
  description = "Repository for release images."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

