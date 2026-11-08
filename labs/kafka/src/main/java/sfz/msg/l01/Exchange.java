package sfz.msg.l01;

import java.util.ArrayList;
import java.util.List;

/**
 * An AMQP 0-9-1 exchange: producers publish to it with a routing key, and it puts a copy of the message into every
 * queue whose binding matches. It stores nothing itself.
 *
 * <ul>
 *   <li>{@code FANOUT} ignores keys: every bound queue gets a copy.</li>
 *   <li>{@code DIRECT} copies the message to the queues bound with a binding key equal to the routing key.</li>
 * </ul>
 * A queue gets at most one copy of a message, however many of its bindings match.
 */
public final class Exchange {
    public enum Type { DIRECT, FANOUT }

    private record Binding(MiniQueue queue, String bindingKey) {}

    private final String name;
    private final Type type;
    private final List<Binding> bindings = new ArrayList<>();

    public Exchange(String name, Type type) {
        this.name = name;
        this.type = type;
    }

    public String getName() {
        return name;
    }

    public Type getType() {
        return type;
    }

    /** Binds {@code queue} to this exchange. A fanout exchange ignores {@code bindingKey}. */
    public void bind(MiniQueue queue, String bindingKey) {
        bindings.add(new Binding(queue, bindingKey));
    }

    /** The queues a message with {@code routingKey} goes to, in binding order, each queue once. */
    public List<MiniQueue> route(String routingKey) {
        throw new UnsupportedOperationException("TODO: FANOUT matches every binding, DIRECT only equal keys; each queue once");
    }

    /**
     * Publishes {@code message} into every queue {@link #route} returns and says how many queues got it. 0 means no
     * binding matched: the message is unroutable, and a broker drops it unless the producer asked to have it returned.
     */
    public int publish(String routingKey, Message message) {
        throw new UnsupportedOperationException("TODO: publish into every queue route() returns, return how many");
    }
}
