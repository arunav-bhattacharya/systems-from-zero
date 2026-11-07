package sfz.kafka.l11.demo

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

private const val REGISTRY = "http://localhost:8081"
private val http: HttpClient = HttpClient.newHttpClient()

private const val V1_SCHEMA = """
{"type": "record", "name": "Payment", "fields": [
  {"name": "id", "type": "string"}, {"name": "account", "type": "string"}, {"name": "amount", "type": "long"}]}"""
private const val V2_SCHEMA = """
{"type": "record", "name": "Payment", "fields": [
  {"name": "id", "type": "string"}, {"name": "account", "type": "string"}, {"name": "amount", "type": "long"},
  {"name": "currency", "type": "string", "default": "EUR"}]}"""
private const val V3_SCHEMA = """
{"type": "record", "name": "Payment", "fields": [
  {"name": "id", "type": "string"}, {"name": "account", "type": "string"}, {"name": "amount", "type": "long"},
  {"name": "currency", "type": "string", "default": "EUR"}, {"name": "merchantId", "type": "string"}]}"""

/**
 * Talks to Schema Registry on localhost:8081 over its REST API: registers version 1 of a payment schema, then asks
 * whether two changes are compatible under the subject's mode, and tries to register both.
 */
fun main() {
    // one subject per run; the serializer's default name for a topic's values is "<topic>-value"
    val subject = "payments-${System.currentTimeMillis() % 100_000}-value"
    call("GET", "/config")
    call("POST", "/subjects/$subject/versions", V1_SCHEMA)                                    // register v1
    call("POST", "/compatibility/subjects/$subject/versions/latest", V2_SCHEMA)               // v2: adds currency, with a default
    call("POST", "/subjects/$subject/versions", V2_SCHEMA)
    call("POST", "/compatibility/subjects/$subject/versions/latest?verbose=true", V3_SCHEMA)  // v3: adds merchantId, no default
    call("POST", "/subjects/$subject/versions", V3_SCHEMA)
    call("GET", "/subjects/$subject/versions")
}

private fun call(method: String, path: String, avroSchema: String? = null) {
    val request = HttpRequest.newBuilder(URI.create(REGISTRY + path)).header("Content-Type", "application/vnd.schemaregistry.v1+json")
    if (avroSchema == null) request.GET() else request.POST(HttpRequest.BodyPublishers.ofString("{\"schema\": ${quote(avroSchema)}}"))
    val response = http.send(request.build(), HttpResponse.BodyHandlers.ofString())
    val line = "$method $path\n  -> ${response.statusCode()} ${summary(response.body())}"
    println(line.replace(Regex("payments-\\d+-value"), "payments-value")) // the subject has this run's number
}

/** The parts of a reply worth reading: ids, verdicts and the reason a change was refused. */
private fun summary(body: String): String {
    val reason = Regex("errorType:\\\\?\"(\\w+)\\\\?\", description:\\\\?\"([^\"\\\\]+)").find(body)
    val head = body.replace(Regex("\"schema\":\".*\""), "\"schema\":...").replace(Regex(",\"messages\":.*|, details: .*|,\"guid\":\"[^\"]*\""), "")
    return if (reason != null) "$head  [${reason.groupValues[1]}: ${reason.groupValues[2]}]" else head
}

private fun quote(json: String) = "\"" + json.trim().replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ") + "\""
