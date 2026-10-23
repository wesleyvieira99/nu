# Fragmento de referência. Provider e backend são externos.
resource "aws_dynamodb_table" "operation_keys" {
  name         = "proposed-operation-keys"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
  lifecycle {
    prevent_destroy = true
  }
  tags = {
    owner       = "proposed-journey-team"
    environment = "example"
  }
}