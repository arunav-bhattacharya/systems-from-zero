// The fraud graph for lesson model-08: accounts, the devices and phones they use, and transfers.
// The same graph as labs/env/neo4j/nosql-11-fraud.cypher; the tests load it before each test.
MATCH (n) DETACH DELETE n;
DROP CONSTRAINT account_id IF EXISTS;

// 13 accounts. A-3101 was flagged by the fraud team this morning.
UNWIND ['A-1001', 'A-2002', 'A-3101', 'A-3102', 'A-3103', 'A-3104', 'A-3105',
        'A-4001', 'A-4002', 'A-4003', 'A-4004', 'A-4005', 'A-4006'] AS id
CREATE (:Account {id: id, flagged: id = 'A-3101'});

// devices and phones: the identifiers accounts log in with
UNWIND ['D-11', 'D-22', 'D-77', 'D-81', 'D-40', 'D-41', 'D-42', 'D-43'] AS id
CREATE (:Device {id: id, kind: 'phone app'});
CREATE (:Device {id: 'D-KIOSK', kind: 'store kiosk'});
UNWIND ['P-0111', 'P-0122', 'P-0177', 'P-0181', 'P-0199', 'P-0140'] AS id
CREATE (:Phone {id: id});

// who uses what
UNWIND [['A-1001', 'D-11'], ['A-1001', 'P-0111'], ['A-2002', 'D-22'], ['A-2002', 'P-0122'],
        ['A-3101', 'D-77'], ['A-3101', 'P-0177'], ['A-3102', 'D-77'], ['A-3102', 'P-0177'],
        ['A-3102', 'P-0199'], ['A-3103', 'P-0199'], ['A-3103', 'D-81'], ['A-3103', 'P-0181'],
        ['A-3104', 'D-81'], ['A-3104', 'P-0181'], ['A-3105', 'D-81'],
        ['A-4001', 'D-40'], ['A-4001', 'P-0140'], ['A-4002', 'D-41'], ['A-4003', 'D-42'],
        ['A-4005', 'D-43'], ['A-4006', 'D-43'],
        // a store kiosk that many customers have tapped: it links people who have nothing in common
        ['A-1001', 'D-KIOSK'], ['A-2002', 'D-KIOSK'], ['A-4002', 'D-KIOSK'], ['A-4003', 'D-KIOSK'],
        ['A-3103', 'D-KIOSK']] AS pair
MATCH (a:Account {id: pair[0]})
MATCH (x {id: pair[1]})
CREATE (a)-[:USES]->(x);

// transfers between accounts, amounts in minor units
UNWIND [['A-3101', 'A-3103', 95000], ['A-3103', 'A-3104', 94000], ['A-3104', 'A-3101', 93000],
        ['A-3102', 'A-3105', 49000], ['A-3105', 'A-4004', 48500], ['A-4004', 'A-3103', 48000],
        ['A-3103', 'A-3102', 47000],
        ['A-1001', 'A-2002', 3000], ['A-2002', 'A-1001', 1500], ['A-4001', 'A-1001', 2000],
        ['A-4005', 'A-4006', 12000]] AS t
MATCH (from:Account {id: t[0]}), (to:Account {id: t[1]})
CREATE (from)-[:TRANSFERRED_TO {amountMinor: t[2]}]->(to);

// a quick count of what is there
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
