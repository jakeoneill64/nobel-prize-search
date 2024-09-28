output "search-service-url" {
  value = "http://${aws_instance.nobel-instance.public_dns}/search"
  description = "The url of the deployed webservice"
}