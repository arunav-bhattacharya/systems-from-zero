#!/bin/sh
# Lesson shard-09: a merchants index with 3 primary shards and 1 replica each, on the three-node cluster.
# Run from the labs folder: sh env/opensearch-cluster/nosql-18-merchants.sh   (safe to run again)
OS=${OS:-http://localhost:9200}
curl -s -X DELETE "$OS/merchants" > /dev/null
# the same text field as lesson store-08, but split into 3 primaries, each with 1 replica
curl -s -X PUT "$OS/merchants" -H 'Content-Type: application/json' -d '{
  "settings": { "number_of_shards": 3, "number_of_replicas": 1 },
  "mappings": { "properties": {
    "name": { "type": "text", "analyzer": "standard" },
    "city": { "type": "keyword" } } }
}' > /dev/null
# twelve merchants: the five from lesson store-08 and seven more
curl -s -X POST "$OS/merchants/_bulk?refresh=true" -H 'Content-Type: application/x-ndjson' --data-binary '
{ "index": { "_id": "M-0042" } }
{ "name": "Northwind Bikes, bike repairs and spare parts", "city": "Leeds" }
{ "index": { "_id": "M-0043" } }
{ "name": "Northwind Coffee", "city": "Leeds" }
{ "index": { "_id": "M-0044" } }
{ "name": "City Bike Rental", "city": "York" }
{ "index": { "_id": "M-0045" } }
{ "name": "Bikes and Boards Outlet, used bikes", "city": "Hull" }
{ "index": { "_id": "M-0046" } }
{ "name": "Harbour Fish Market", "city": "Hull" }
{ "index": { "_id": "M-0047" } }
{ "name": "Station Bakery", "city": "York" }
{ "index": { "_id": "M-0048" } }
{ "name": "Riverside Books", "city": "Leeds" }
{ "index": { "_id": "M-0049" } }
{ "name": "Moor Cycle Works", "city": "Harrogate" }
{ "index": { "_id": "M-0050" } }
{ "name": "Old Mill Pharmacy", "city": "York" }
{ "index": { "_id": "M-0051" } }
{ "name": "Quayside Florist", "city": "Hull" }
{ "index": { "_id": "M-0052" } }
{ "name": "Abbey Garage", "city": "Whitby" }
{ "index": { "_id": "M-0053" } }
{ "name": "Dales Outdoor Shop", "city": "Skipton" }
' > /dev/null
# wait until every primary and replica is copied
curl -s "$OS/_cluster/health/merchants?wait_for_status=green&wait_for_no_relocating_shards=true&timeout=60s&filter_path=status"
echo
