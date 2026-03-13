# Create the bucket before running terraform init:
#   gsutil mb -l us-central1 gs://hsv-terraform-state
terraform {
  backend "gcs" {
    bucket = "hsv-terraform-state"
    prefix = "hausa-voice-swarm"
  }
}
