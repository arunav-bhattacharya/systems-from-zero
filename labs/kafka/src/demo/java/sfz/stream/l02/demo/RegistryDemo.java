package sfz.stream.l02.demo;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Talks to Schema Registry on localhost:8081 over its REST API: registers version 1 of a payment schema, then asks
 * whether two changes are compatible under the subject's mode, and tries to register both.
 */
public class RegistryDemo {
    static final String REGISTRY = "http://localhost:8081";
    static final HttpClient http = HttpClient.newHttpClient();

    static final String V1 = """
            {"type": "record", "name": "Payment", "fields": [
              {"name": "id", "type": "string"}, {"name": "account", "type": "string"}, {"name": "amount", "type": "long"}]}""";
    static final String V2 = """
            {"type": "record", "name": "Payment", "fields": [
              {"name": "id", "type": "string"}, {"name": "account", "type": "string"}, {"name": "amount", "type": "long"},
              {"name": "currency", "type": "string", "default": "EUR"}]}""";
    static final String V3 = """
            {"type": "record", "name": "Payment", "fields": [
              {"name": "id", "type": "string"}, {"name": "account", "type": "string"}, {"name": "amount", "type": "long"},
              {"name": "currency", "type": "string", "default": "EUR"}, {"name": "merchantId", "type": "string"}]}""";

    public static void main(String[] args) throws Exception {
        // one subject per run; the serializer's default name for a topic's values is "<topic>-value"
        String subject = "payments-" + System.currentTimeMillis() % 100_000 + "-value";
        call("GET", "/config", null);
        call("POST", "/subjects/" + subject + "/versions", V1);                                   // register v1
        call("POST", "/compatibility/subjects/" + subject + "/versions/latest", V2);              // v2: adds currency, with a default
        call("POST", "/subjects/" + subject + "/versions", V2);
        call("POST", "/compatibility/subjects/" + subject + "/versions/latest?verbose=true", V3); // v3: adds merchantId, no default
        call("POST", "/subjects/" + subject + "/versions", V3);
        call("GET", "/subjects/" + subject + "/versions", null);
    }

    static void call(String method, String path, String avroSchema) throws Exception {
        var request = HttpRequest.newBuilder(URI.create(REGISTRY + path)).header("Content-Type", "application/vnd.schemaregistry.v1+json");
        if (avroSchema == null) request.GET();
        else request.POST(HttpRequest.BodyPublishers.ofString("{\"schema\": " + quote(avroSchema) + "}"));
        HttpResponse<String> response = http.send(request.build(), HttpResponse.BodyHandlers.ofString());
        String line = method + " " + path + "\n  -> " + response.statusCode() + " " + summary(response.body());
        System.out.println(line.replaceAll("payments-\\d+-value", "payments-value"));   // the subject has this run's number
    }

    /** The parts of a reply worth reading: ids, verdicts and the reason a change was refused. */
    static String summary(String body) {
        Matcher reason = Pattern.compile("errorType:\\\\?\"(\\w+)\\\\?\", description:\\\\?\"([^\"\\\\]+)").matcher(body);
        String head = body.replaceAll("\"schema\":\".*\"", "\"schema\":...").replaceAll(",\"messages\":.*|, details: .*|,\"guid\":\"[^\"]*\"", "");
        return reason.find() ? head + "  [" + reason.group(1) + ": " + reason.group(2) + "]" : head;
    }

    static String quote(String json) {
        return "\"" + json.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ") + "\"";
    }
}
