#!/bin/sh
# Lesson nosql-12: a merchants index with five merchants, for the search Try-it.
# Run from the labs folder: sh env/opensearch/nosql-12-merchants.sh   (safe to run again)
OS=${OS:-http://localhost:9200}
curl -s -X DELETE "$OS/merchants" > /dev/null
# one text field with the standard analyzer, and one copy with the english analyzer (stemming)
curl -s -X PUT "$OS/merchants" -H 'Content-Type: application/json' -d '{
  "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
  "mappings": { "properties": {
    "name": { "type": "text", "analyzer": "standard",
              "fields": { "english": { "type": "text", "analyzer": "english" } } } } }
}' > /dev/null
curl -s -X POST "$OS/merchants/_bulk?refresh=true" -H 'Content-Type: application/x-ndjson' --data-binary '
{ "index": { "_id": "M-0042" } }
{ "name": "Northwind Bikes, bike repairs and spare parts" }
{ "index": { "_id": "M-0043" } }
{ "name": "Northwind Coffee" }
{ "index": { "_id": "M-0044" } }
{ "name": "City Bike Rental" }
{ "index": { "_id": "M-0045" } }
{ "name": "Bikes and Boards Outlet, used bikes" }
{ "index": { "_id": "M-0046" } }
{ "name": "Harbour Fish Market" }
' > /dev/null
curl -s "$OS/merchants/_count?filter_path=count"
echo
