variable "region" {
  description = "The region in which to deploy"
  type        = string
}

variable "vpc_id" {
  description = "The name of the VPC in which you want to deploy"
  type        = string
}

variable "ingress_cidr" {
  description = "The address from which the instance will accept all kinds of traffic"
  type        = string
}