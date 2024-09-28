provider "aws" {
  region = var.region # Change this to your preferred AWS region
}

resource "aws_instance" "nobel-instance" {
  ami           = "ami-01ec84b284795cbc7"
  instance_type = "t2.medium"

  security_groups = [aws_security_group.nobel-sg.name]
  user_data = file("../env-setup.sh")

  root_block_device {
    volume_size = 50
  }

  tags = {
    lifecycle: "transient"
  }
}

resource "aws_security_group" "nobel-sg" {
  name        = "nobel-sg"
  description = "Allow inbound traffic on port 80 and 22 from approved cidr block"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.ingress_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    lifecycle: "transient"
  }
}

