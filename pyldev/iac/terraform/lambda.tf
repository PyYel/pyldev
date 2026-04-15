data "archive_file" "handle_users_login" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/handle_users_login"
  output_path = "${path.module}/../.terraform/handle_users_login.zip"
}

resource "aws_lambda_function" "user_service" {
  filename         = data.archive_file.handle_users_login.output_path
  function_name    = "${var.app_name}-user-service"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.handle_users_login.output_base64sha256

  environment {
    variables = {
      CLIENT_ID    = aws_cognito_user_pool_client.client.id
      USER_POOL_ID = aws_cognito_user_pool.pool.id
      TABLE_NAME   = aws_dynamodb_table.users.name
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }
}