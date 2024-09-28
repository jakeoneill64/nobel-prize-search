# Deployment nobel laureate search service using terraform, kubernetes, python and bash.

__Steps to deploy:__

1. Install terraform & Git https://developer.hashicorp.com/terraform/install https://git-scm.com/downloads
2. `git clone https://github.com/jakeoneill64/nobel-prize-search`
3. navigate to `./terraform`
4. `terraform init`
5. fill in the variables for deployment in `terraform.tfvars`.
6. `terraform apply`

_the result should look something like_

```Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

search-service-url = "http://ec2-ip.eu-west-2.compute.amazonaws.com/search"
```

You can use this url to access the search service. The search service takes up to three parameters.

As an example, if you wanted to search for all `chemistry` laureates which contain the word `ubiquitin` whose name is `Hershko` you would send the request

`curl -X GET 'http://search-service-hostname/search?category=chemistry&description=ubiquitin&name=Hershko'`

__Naturally, URL parameters must be URL encoded if you have special characters, such as spaces (%20)__


__NB the deployment takes longer than the terraform application steps, so the endpoint will not be immediately available.__