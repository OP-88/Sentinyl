"""
Typosquatting Detection Worker
Generates domain variations and performs DNS resolution to detect active threats
"""
import json
import time
from typing import List, Dict, Any, Optional
import dns.resolver
from loguru import logger
import socket

from workers.shared_utils import (
    get_redis_connection,
    update_job_status,
    save_threat,
    retry_on_failure
)
from workers.slack_utils import SlackNotifier


class DomainFuzzer:
    """
    Domain fuzzing engine to generate typosquatting variations
    Implements DNSTwist-like permutation logic
    """
    
    # Common TLD variations
    COMMON_TLDS = [
        'com', 'net', 'org', 'co', 'io', 'app', 'dev', 'ai',
        'info', 'biz', 'online', 'site', 'tech', 'store'
    ]
    
    # Character substitutions (homoglyphs)
    HOMOGLYPHS = {
        'a': ['4', '@'],
        'e': ['3'],
        'i': ['1', 'l'],
        'o': ['0'],
        's': ['5', '$'],
        'l': ['1', 'i'],
        'g': ['9'],
        'b': ['8']
    }
    
    def __init__(self, domain: str):
        """
        Initialize fuzzer with target domain
        
        Args:
            domain: Target domain (e.g., 'example.com')
        """
        self.domain = domain.lower().strip()
        
        # Split domain into parts
        if '.' in self.domain:
            parts = self.domain.rsplit('.', 1)
            self.name = parts[0]
            self.tld = parts[1] if len(parts) > 1 else 'com'
        else:
            self.name = self.domain
            self.tld = 'com'
        
        logger.info(f"Initialized DomainFuzzer for: {self.domain} (name={self.name}, tld={self.tld})")
    
    def generate_variations(self) -> List[str]:
        """
        Generate all domain variations
        
        Returns:
            List of domain variation strings
        """
        variations = set()
        
        # 1. Character omission (missing letters)
        variations.update(self._omission())
        
        # 2. Character repetition (double letters)
        variations.update(self._repetition())
        
        # 3. Adjacent character swap
        variations.update(self._transposition())
        
        # 4. Homoglyph substitution
        variations.update(self._homoglyph())
        
        # 5. Common typos (adjacent keyboard keys)
        variations.update(self._keyboard_typos())
        
        # 6. TLD variations
        variations.update(self._tld_swap())
        
        # 7. Hyphenation
        variations.update(self._hyphenation())
        
        # 8. Subdomain addition
        variations.update(self._subdomain_prefix())
        
        # Remove original domain
        variations.discard(self.domain)
        
        logger.info(f"Generated {len(variations)} domain variations")
        return list(variations)
    
    def _omission(self) -> List[str]:
        """Remove one character at a time"""
        results = []
        for i in range(len(self.name)):
            variant = self.name[:i] + self.name[i+1:]
            if len(variant) > 2:  # Avoid too short domains
                results.append(f"{variant}.{self.tld}")
        return results
    
    def _repetition(self) -> List[str]:
        """Double each character"""
        results = []
        for i in range(len(self.name)):
            variant = self.name[:i] + self.name[i] + self.name[i:]
            results.append(f"{variant}.{self.tld}")
        return results
    
    def _transposition(self) -> List[str]:
        """Swap adjacent characters"""
        results = []
        for i in range(len(self.name) - 1):
            chars = list(self.name)
            chars[i], chars[i+1] = chars[i+1], chars[i]
            variant = ''.join(chars)
            results.append(f"{variant}.{self.tld}")
        return results
    
    def _homoglyph(self) -> List[str]:
        """Replace characters with visually similar ones"""
        results = []
        for i, char in enumerate(self.name):
            if char in self.HOMOGLYPHS:
                for substitute in self.HOMOGLYPHS[char]:
                    variant = self.name[:i] + substitute + self.name[i+1:]
                    results.append(f"{variant}.{self.tld}")
        return results
    
    def _keyboard_typos(self) -> List[str]:
        """Simulate keyboard layout typos (QWERTY)"""
        keyboard = {
            'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'],
            'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
            'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
            'p': ['o', 'l'], 'a': ['q', 's', 'z'], 's': ['a', 'w', 'd', 'x'],
            'd': ['s', 'e', 'f', 'c'], 'f': ['d', 'r', 'g', 'v'], 
            'g': ['f', 't', 'h', 'b'], 'h': ['g', 'y', 'j', 'n'],
            'j': ['h', 'u', 'k', 'm'], 'k': ['j', 'i', 'l'], 'l': ['k', 'o'],
            'z': ['a', 'x'], 'x': ['z', 's', 'c'], 'c': ['x', 'd', 'v'],
            'v': ['c', 'f', 'b'], 'b': ['v', 'g', 'n'], 'n': ['b', 'h', 'm'],
            'm': ['n', 'j']
        }
        
        results = []
        for i, char in enumerate(self.name):
            if char in keyboard:
                for adjacent in keyboard[char][:2]:  # Limit to 2 most common
                    variant = self.name[:i] + adjacent + self.name[i+1:]
                    results.append(f"{variant}.{self.tld}")
        return results
    
    def _tld_swap(self) -> List[str]:
        """Replace TLD with common alternatives"""
        results = []
        for tld in self.COMMON_TLDS:
            if tld != self.tld:
                results.append(f"{self.name}.{tld}")
        return results
    
    def _hyphenation(self) -> List[str]:
        """Add hyphens between characters"""
        results = []
        if len(self.name) >= 4:
            # Add hyphen at different positions
            for i in range(2, len(self.name) - 1):
                variant = self.name[:i] + '-' + self.name[i:]
                results.append(f"{variant}.{self.tld}")
        return results
    
    def _subdomain_prefix(self) -> List[str]:
        """Add common subdomain prefixes"""
        prefixes = ['www', 'secure', 'login', 'account', 'verify', 'update']
        results = []
        for prefix in prefixes:
            results.append(f"{prefix}-{self.name}.{self.tld}")
            results.append(f"{prefix}{self.name}.{self.tld}")
        return results
    
    @retry_on_failure(max_retries=2, delay=1)
    def resolve_dns(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Resolve DNS for a domain
        
        Args:
            domain: Domain to resolve
        
        Returns:
            Dictionary with DNS information or None if not resolvable
        """
        try:
            # Get A record (IPv4)
            answers = dns.resolver.resolve(domain, 'A', lifetime=3)
            ip_addresses = [str(rdata) for rdata in answers]
            
            # Get nameservers
            try:
                ns_answers = dns.resolver.resolve(domain, 'NS', lifetime=3)
                nameservers = [str(rdata) for rdata in ns_answers]
            except:
                nameservers = []
            
            return {
                "domain": domain,
                "ip_addresses": ip_addresses,
                "nameservers": nameservers,
                "active": True
            }
            
        except dns.resolver.NXDOMAIN:
            # Domain doesn't exist
            return None
        except dns.resolver.NoAnswer:
            # Domain exists but no A record
            return None
        except dns.resolver.Timeout:
            logger.warning(f"DNS timeout for {domain}")
            return None
        except Exception as e:
            logger.debug(f"DNS resolution failed for {domain}: {e}")
            return None
    
    def scan(self, job_id: str, slack_notifier: Optional[SlackNotifier] = None) -> List[Dict[str, Any]]:
        """
        Perform complete typosquatting scan
        
        Args:
            job_id: Scan job ID
            slack_notifier: Optional Slack notifier for immediate alerts
        
        Returns:
            List of active threats found
        """
        logger.info(f"Starting typosquat scan for {self.domain} (job: {job_id})")
        
        variations = self.generate_variations()
        active_threats = []
        
        # Initialize Slack notifier if not provided
        if slack_notifier is None:
            slack_notifier = SlackNotifier()
        
        # Scan each variation
        for i, variant in enumerate(variations):
            if i % 50 == 0:
                logger.info(f"Scanned {i}/{len(variations)} variations...")
            
            dns_info = self.resolve_dns(variant)
            if dns_info:
                logger.warning(f"🚨 Active threat detected: {variant} -> {dns_info['ip_addresses']}")
                
                threat = {
                    "job_id": job_id,
                    "original_domain": self.domain,
                    "malicious_domain": variant,
                    "threat_type": "typosquat",
                    "severity": "CRITICAL",  # Always CRITICAL for active typosquats
                    "ip_address": dns_info['ip_addresses'][0] if dns_info['ip_addresses'] else None,
                    "nameservers": dns_info.get('nameservers', [])
                }
                
                active_threats.append(threat)
                
                # Save to database
                save_threat(threat)
                
                # IMMEDIATELY send Slack alert for CRITICAL threat
                slack_notifier.send_alert(
                    domain=self.domain,
                    threat_type="typosquat",
                    severity="CRITICAL",
                    details={
                        "malicious_domain": variant,
                        "ip_address": threat["ip_address"],
                        "nameservers": threat["nameservers"]
                    }
                )
            
            # Rate limiting
            time.sleep(0.1)
        
        logger.info(f"Scan complete. Found {len(active_threats)} active threats")
        return active_threats


def process_typosquat_job(job_data: Dict[str, Any]) -> None:
    """
    Process a typosquatting scan job from the queue
    
    Args:
        job_data: Job payload from Redis
    """
    job_id = job_data.get("job_id")
    domain = job_data.get("domain")
    
    logger.info(f"Processing typosquat job {job_id} for domain: {domain}")
    
    try:
        # Update status to processing
        update_job_status(job_id, "processing")
        
        # Initialize Slack notifier
        slack_notifier = SlackNotifier()
        
        # Run scan (Slack alerts sent immediately for each threat)
        fuzzer = DomainFuzzer(domain)
        threats = fuzzer.scan(job_id, slack_notifier)
        
        # Send summary after scan completes
        if threats:
            critical_count = sum(1 for t in threats if t.get("severity") == "CRITICAL")
            slack_notifier.send_summary(
                domain=domain,
                scan_type="typosquat",
                total_threats=len(threats),
                critical_threats=critical_count
            )
        
        # Mark as completed
        update_job_status(job_id, "completed")
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job_status(job_id, "failed", str(e))


def main():
    """Main worker loop"""
    logger.info("Typosquat worker started")
    
    redis_client = get_redis_connection()
    queue_name = "queue:typosquat"
    
    logger.info(f"Listening on queue: {queue_name}")
    
    while True:
        try:
            # Block and wait for jobs (BRPOP with 5 second timeout)
            result = redis_client.brpop(queue_name, timeout=5)
            
            if result:
                _, job_payload = result
                job_data = json.loads(job_payload)
                
                logger.info(f"Received job: {job_data}")
                process_typosquat_job(job_data)
            
        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    main()
