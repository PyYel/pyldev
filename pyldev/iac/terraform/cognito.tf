resource "aws_cognito_user_pool" "pool" {
  name = "${var.app_name}-user-pool"
  auto_verified_attributes = ["email"]
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.app_name}-client"
  user_pool_id = aws_cognito_user_pool.pool.id
}