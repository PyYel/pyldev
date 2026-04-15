resource "aws_dynamodb_table" "users" {
  name         = "${var.app_name}-user-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "UserId"

  attribute {
    name = "UserId"
    type = "S"
  }
}