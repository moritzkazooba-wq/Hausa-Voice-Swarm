# Confluent Cloud Kafka — Placeholder Module
#
# This module provides the variable interface and outputs for Confluent Cloud.
# To activate, add the Confluent provider to infrastructure/versions.tf:
#
#   confluent = {
#     source  = "confluentinc/confluent"
#     version = "~> 1.0"
#   }
#
# Then uncomment the resources below and configure credentials.

# provider "confluent" {
#   cloud_api_key    = var.confluent_api_key
#   cloud_api_secret = var.confluent_api_secret
# }

# resource "confluent_kafka_cluster" "hsv" {
#   display_name = "hsv-${var.environment}"
#   availability = "SINGLE_ZONE"
#   cloud        = "GCP"
#   region       = var.region
#
#   basic {}
#
#   environment {
#     id = var.confluent_environment_id
#   }
# }

# resource "confluent_kafka_topic" "intents" {
#   kafka_cluster { id = confluent_kafka_cluster.hsv.id }
#   topic_name       = "hsv.intents"
#   partitions_count = 6
#   config           = { "retention.ms" = "604800000" }  # 7 days
# }

# resource "confluent_kafka_topic" "tools" {
#   kafka_cluster { id = confluent_kafka_cluster.hsv.id }
#   topic_name       = "hsv.tools"
#   partitions_count = 6
#   config           = { "retention.ms" = "604800000" }
# }

# resource "confluent_kafka_topic" "sessions" {
#   kafka_cluster { id = confluent_kafka_cluster.hsv.id }
#   topic_name       = "hsv.sessions"
#   partitions_count = 6
#   config           = { "retention.ms" = "604800000" }
# }

# resource "confluent_kafka_topic" "escalations" {
#   kafka_cluster { id = confluent_kafka_cluster.hsv.id }
#   topic_name       = "hsv.escalations"
#   partitions_count = 6
#   config           = { "retention.ms" = "604800000" }
# }
