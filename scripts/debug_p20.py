import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import Database
import json

def debug_p20():
    db = Database()
    driver = db.connect_neo4j()
    with driver.session() as session:
        print("Checking Patient P20...")
        res = session.run("MATCH (n:Patient {patientId: 'P20'}) RETURN n, labels(n) as labels").single()
        if res:
            print(f"Found Node: {res['n']}")
            print(f"Labels: {res['labels']}")
        else:
            print("P20 NOT FOUND with label :Patient and patientId 'P20'")

        print("\nChecking Entity P20...")
        res = session.run("MATCH (n:Entity {name: 'P20'}) RETURN n").single()
        if res:
            print(f"Found Entity: {res['n']}")
        else:
            print("P20 NOT FOUND with label :Entity and name 'P20'")
            
        print("\nChecking all labels for P20...")
        res = session.run("MATCH (n) WHERE n.patientId = 'P20' RETURN labels(n) as l, n").single()
        if res:
            print(f"Found Node with patientId 'P20'. Labels: {res['l']}")
        else:
            print("No node found with patientId 'P20'")

        print("\nChecking relationships for P20...")
        res = session.run("MATCH (p {patientId: 'P20'})-[r]->(neighbor) RETURN type(r) as rel, labels(neighbor) as l, neighbor.name as n, neighbor.visitId as v_id")
        for rec in res:
            print(f"Relationship: {rec['rel']} -> {rec['l']} ({rec['n'] if rec['n'] else rec['v_id']})")

    db.close()

if __name__ == "__main__":
    debug_p20()
