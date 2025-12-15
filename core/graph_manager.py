"""
Neo4j Graph Manager for Sentinyl Enterprise
Manages investigation graph: Domain → IP → Actor → Repository relationships
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError
from loguru import logger
import os


@dataclass
class GraphNode:
    """Represents a node in the investigation graph"""
    id: str
    label: str  # Domain, IP_Address, Actor, Repository, Secret
    properties: Dict[str, Any]


@dataclass
class GraphRelationship:
    """Represents a relationship between nodes"""
    from_node: str
    to_node: str
    rel_type: str  # RESOLVES_TO, REGISTERED_BY, EXPOSES, OWNED_BY, HOSTS
    properties: Dict[str, Any]


class GraphManager:
    """
    Neo4j Graph Database Manager
    
    Schema:
        (Domain)-[RESOLVES_TO]->(IP_Address)
        (Domain)-[REGISTERED_BY]->(Actor)
        (Repository)-[EXPOSES]->(Secret)
        (Repository)-[OWNED_BY]->(Actor)
        (IP_Address)-[HOSTS]->(Repository)
        (Actor)-[CONTROLS]->(Domain)
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j bolt URI (default: from NEO4J_URI env var)
            user: Neo4j username (default: from NEO4J_USER env var)
            password: Neo4j password (default: from NEO4J_PASSWORD env var)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver: Optional[Driver] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except AuthError:
            logger.error("Neo4j authentication failed - check credentials")
            raise
        except ServiceUnavailable:
            logger.warning(
                f"Neo4j unavailable at {self.uri} - graph features disabled"
            )
            self.driver = None
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def is_available(self) -> bool:
        """Check if graph database is available"""
        return self.driver is not None
    
    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
        unique_key: str = "id"
    ) -> Optional[str]:
        """
        Create or merge a node in the graph
        
        Args:
            label: Node label (Domain, IP_Address, Actor, Repository, Secret)
            properties: Node properties (must include unique_key)
            unique_key: Property name to use for uniqueness constraint
            
        Returns:
            Node ID if successful, None otherwise
        """
        if not self.is_available():
            logger.warning("Graph unavailable - skipping node creation")
            return None
        
        if unique_key not in properties:
            logger.error(f"Properties must include '{unique_key}' for uniqueness")
            return None
        
        try:
            with self.driver.session() as session:
                result = session.execute_write(
                    self._create_node_tx, label, properties, unique_key
                )
                logger.info(f"Created/merged {label} node: {properties[unique_key]}")
                return result
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            return None
    
    @staticmethod
    def _create_node_tx(tx, label: str, properties: Dict[str, Any], unique_key: str):
        """Transaction function to create/merge node"""
        # Build properties string for Cypher
        props_str = ", ".join(
            [f"{k}: ${k}" for k in properties.keys()]
        )
        
        query = f"""
        MERGE (n:{label} {{{unique_key}: ${unique_key}}})
        SET n += {{{props_str}}}
        RETURN n.{unique_key} as id
        """
        
        result = tx.run(query, **properties)
        record = result.single()
        return record["id"] if record else None
    
    def create_relationship(
        self,
        from_node_label: str,
        from_node_id: str,
        rel_type: str,
        to_node_label: str,
        to_node_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create relationship between two nodes
        
        Args:
            from_node_label: Source node label
            from_node_id: Source node ID value
            rel_type: Relationship type (e.g., RESOLVES_TO, EXPOSES)
            to_node_label: Target node label
            to_node_id: Target node ID value
            properties: Optional relationship properties
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        if properties is None:
            properties = {}
        
        try:
            with self.driver.session() as session:
                session.execute_write(
                    self._create_relationship_tx,
                    from_node_label, from_node_id,
                    rel_type,
                    to_node_label, to_node_id,
                    properties
                )
                logger.info(
                    f"Created relationship: ({from_node_label})-[{rel_type}]->({to_node_label})"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    @staticmethod
    def _create_relationship_tx(
        tx,
        from_label: str, from_id: str,
        rel_type: str,
        to_label: str, to_id: str,
        properties: Dict[str, Any]
    ):
        """Transaction function to create relationship"""
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        props_clause = f"{{{props_str}}}" if properties else ""
        
        query = f"""
        MATCH (a:{from_label} {{id: $from_id}})
        MATCH (b:{to_label} {{id: $to_id}})
        MERGE (a)-[r:{rel_type} {props_clause}]->(b)
        RETURN r
        """
        
        params = {
            "from_id": from_id,
            "to_id": to_id,
            **properties
        }
        
        tx.run(query, **params)
    
    def ingest_finding(
        self,
        entity_type: str,
        properties: Dict[str, Any],
        relations: Optional[List[Tuple[str, str, Dict[str, Any]]]] = None
    ) -> bool:
        """
        High-level method to ingest a complete finding into the graph
        
        Args:
            entity_type: Primary node type (Domain, Repository, etc.)
            properties: Properties for the primary node
            relations: List of (rel_type, target_entity, target_props) tuples
            
        Example:
            graph.ingest_finding(
                entity_type="Domain",
                properties={"id": "evil.com", "malicious": True},
                relations=[
                    ("RESOLVES_TO", "IP_Address", {"id": "1.2.3.4", "location": "US"}),
                    ("REGISTERED_BY", "Actor", {"id": "attacker@evil.com"})
                ]
            )
        
        Returns:
            True if successful
        """
        if not self.is_available():
            return False
        
        # Create primary node
        node_id = self.create_node(entity_type, properties)
        if not node_id:
            return False
        
        # Create relationships
        if relations:
            for rel_type, target_label, target_props in relations:
                # Create target node
                target_id = self.create_node(target_label, target_props)
                if target_id:
                    # Create relationship
                    self.create_relationship(
                        entity_type, node_id,
                        rel_type,
                        target_label, target_id
                    )
        
        return True
    
    def query_investigation_path(
        self,
        start_node_label: str,
        start_node_id: str,
        end_node_label: str,
        end_node_id: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find paths between two nodes (for investigation)
        
        Args:
            start_node_label: Starting node label
            start_node_id: Starting node ID
            end_node_label: Ending node label
            end_node_id: Ending node ID
            max_depth: Maximum relationship hops
            
        Returns:
            List of paths with nodes and relationships
        """
        if not self.is_available():
            return []
        
        try:
            with self.driver.session() as session:
                result = session.execute_read(
                    self._query_path_tx,
                    start_node_label, start_node_id,
                    end_node_label, end_node_id,
                    max_depth
                )
                return result
        except Exception as e:
            logger.error(f"Failed to query path: {e}")
            return []
    
    @staticmethod
    def _query_path_tx(
        tx,
        start_label: str, start_id: str,
        end_label: str, end_id: str,
        max_depth: int
    ):
        """Transaction function to find paths"""
        query = f"""
        MATCH path = (start:{start_label} {{id: $start_id}})
                     -[*1..{max_depth}]->
                     (end:{end_label} {{id: $end_id}})
        RETURN path
        LIMIT 10
        """
        
        result = tx.run(query, start_id=start_id, end_id=end_id)
        return [record["path"] for record in result]
    
    def get_node_connections(
        self,
        node_label: str,
        node_id: str,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get all connections for a specific node
        
        Args:
            node_label: Node label
            node_id: Node ID
            direction: "incoming", "outgoing", or "both"
            
        Returns:
            List of connected nodes with relationship info
        """
        if not self.is_available():
            return []
        
        try:
            with self.driver.session() as session:
                result = session.execute_read(
                    self._get_connections_tx,
                    node_label, node_id, direction
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get connections: {e}")
            return []
    
    @staticmethod
    def _get_connections_tx(tx, node_label: str, node_id: str, direction: str):
        """Transaction function to get node connections"""
        if direction == "incoming":
            pattern = "(related)-[r]->(node)"
        elif direction == "outgoing":
            pattern = "(node)-[r]->(related)"
        else:  # both
            pattern = "(node)-[r]-(related)"
        
        query = f"""
        MATCH {pattern}
        WHERE node:{node_label} AND node.id = $node_id
        RETURN type(r) as relationship,
               labels(related) as labels,
               properties(related) as properties
        LIMIT 50
        """
        
        result = tx.run(query, node_id=node_id)
        return [dict(record) for record in result]


# Context manager support
class GraphManagerContext:
    """Context manager for GraphManager"""
    def __init__(self, *args, **kwargs):
        self.manager = GraphManager(*args, **kwargs)
    
    def __enter__(self):
        return self.manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.close()
        return False
