# ECR Repository for model containers
resource "aws_ecr_repository" "models" {
  name                 = "${var.project_name}-models-${var.environment}"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "AES256"
  }
  
  tags = merge(local.common_tags, {
    Name = "ServeML Model Repository"
  })
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "models" {
  repository = aws_ecr_repository.models.name
  
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 50 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 50
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECR Repository for base images
resource "aws_ecr_repository" "base_images" {
  name                 = "${var.project_name}-base-${var.environment}"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "AES256"
  }
  
  tags = merge(local.common_tags, {
    Name = "ServeML Base Images"
  })
}