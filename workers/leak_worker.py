"""
GitHub Leak Detection Worker
Scans GitHub for exposed credentials and sensitive data
"""
import json
import time
from typing import List, Dict, Any, Optional
from github import Github, GithubException, RateLimitExceededException
from loguru import logger

from workers.shared_utils import (
    get_redis_connection,
    update_job_status,
    save_leak,
    retry_on_failure
)
from workers.slack_utils import SlackNotifier
import os


class LeakHunter:
    """
    GitHub leak detection scanner
    Searches for exposed credentials and sensitive information
    """
    
    # Keywords to search for alongside domain
    SENSITIVE_KEYWORDS = [
        'password',
        'api_key',
        'apikey',
        'secret',
        'token',
        'credentials',
        'private_key',
        'access_key',
        'secret_key',
        'auth',
        'authentication'
    ]
    
    # File extensions to prioritize
    RELEVANT_EXTENSIONS = [
        '.env',
        '.config',
        '.json',
        '.yml',
        '.yaml',
        '.xml',
        '.txt',
        '.py',
        '.js',
        '.java',
        '.php',
        '.rb'
    ]
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize leak hunter
        
        Args:
            github_token: GitHub personal access token (optional but recommended)
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        
        if not self.github_token:
            logger.warning("No GitHub token provided - rate limits will be very restrictive (60 req/hour)")
            self.github = Github()  # Unauthenticated
        else:
            self.github = Github(self.github_token)
            logger.info("Authenticated GitHub API client initialized")
        
        # Check rate limit
        self._check_rate_limit()
    
    def _check_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status
        
        Returns:
            Dictionary with rate limit info
        """
        try:
            rate_limit = self.github.get_rate_limit()
            core_limit = rate_limit.core
            
            rate_info = {
                "remaining": core_limit.remaining,
                "limit": core_limit.limit,
                "reset_time": core_limit.reset
            }
            
            logger.info(f"GitHub API Rate Limit: {core_limit.remaining}/{core_limit.limit} (resets at {core_limit.reset})")
            
            if core_limit.remaining < 10:
                logger.warning(f"⚠️ Low rate limit: {core_limit.remaining} requests remaining")
            
            return rate_info
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return {"remaining": 0, "limit": 0}
    
    def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit is exceeded"""
        try:
            rate_limit = self.github.get_rate_limit()
            if rate_limit.core.remaining == 0:
                reset_time = rate_limit.core.reset
                wait_seconds = (reset_time - time.time()).total_seconds() + 60
                
                logger.warning(f"Rate limit exceeded. Waiting {wait_seconds/60:.1f} minutes...")
                time.sleep(wait_seconds)
        except Exception as e:
            logger.error(f"Error handling rate limit: {e}")
            time.sleep(300)  # Wait 5 minutes as fallback
    
    def search_github_code(
        self,
        domain: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search GitHub code for domain + sensitive keywords
        
        Args:
            domain: Target domain to search for
            max_results: Maximum number of results to process
        
        Returns:
            List of potential leaks found
        """
        leaks = []
        
        for keyword in self.SENSITIVE_KEYWORDS:
            try:
                # Check rate limit before each search
                rate_info = self._check_rate_limit()
                if rate_info.get("remaining", 0) < 5:
                    self._wait_for_rate_limit()
                
                # Construct search query
                # Format: "domain keyword" in:file language:python
                query = f'"{domain}" {keyword}'
                
                logger.info(f"Searching: {query}")
                
                # Execute search
                results = self.github.search_code(query, order='desc')
                
                # Process results
                processed = 0
                for code_result in results:
                    if processed >= max_results:
                        break
                    
                    try:
                        # Extract information
                        repo = code_result.repository
                        file_path = code_result.path
                        
                        # Get content snippet (limited to avoid huge responses)
                        try:
                            content = code_result.decoded_content.decode('utf-8')[:500]
                        except:
                            content = "[Binary or unreadable content]"
                        
                        leak_info = {
                            "repository_url": repo.html_url,
                            "repository_name": repo.full_name,
                            "file_path": file_path,
                            "snippet": content,
                            "leak_type": keyword,
                            "severity": self._classify_severity(keyword, content),
                            "is_public": not repo.private,
                            "stars": repo.stargazers_count,
                            "last_updated": repo.updated_at.isoformat() if repo.updated_at else None
                        }
                        
                        leaks.append(leak_info)
                        processed += 1
                        
                        logger.warning(f"🔍 Potential leak found: {repo.full_name}/{file_path}")
                        
                    except Exception as e:
                        logger.debug(f"Error processing code result: {e}")
                        continue
                
                # Rate limiting between searches
                time.sleep(2)
                
            except RateLimitExceededException:
                logger.warning("Rate limit exceeded during search")
                self._wait_for_rate_limit()
                continue
                
            except GithubException as e:
                if e.status == 403:
                    logger.warning("Secondary rate limit hit, waiting 60s...")
                    time.sleep(60)
                else:
                    logger.error(f"GitHub API error: {e}")
                continue
                
            except Exception as e:
                logger.error(f"Search error for keyword '{keyword}': {e}")
                continue
        
        logger.info(f"GitHub search complete. Found {len(leaks)} potential leaks")
        return leaks
    
    def _classify_severity(self, keyword: str, content: str) -> str:
        """
        Classify leak severity based on keyword and content
        
        Args:
            keyword: Matched keyword
            content: Code snippet content
        
        Returns:
            Severity level (low, medium, high, critical)
        """
        # Critical keywords
        critical_keywords = ['private_key', 'secret_key', 'api_key', 'password']
        if keyword in critical_keywords:
            # Check if it looks like actual credentials (not just variable names)
            if any(char in content for char in ['=', ':', '"', "'"]):
                return "critical"
            return "high"
        
        # High severity
        high_keywords = ['token', 'credentials', 'access_key']
        if keyword in high_keywords:
            return "high"
        
        # Medium severity
        return "medium"
    
    def scan(self, domain: str, job_id: str, slack_notifier: Optional[SlackNotifier] = None) -> List[Dict[str, Any]]:
        """
        Perform complete GitHub leak scan
        
        Args:
            domain: Target domain
            job_id: Scan job ID
            slack_notifier: Optional Slack notifier for immediate alerts
        
        Returns:
            List of leaks found
        """
        logger.info(f"Starting GitHub leak scan for {domain} (job: {job_id})")
        
        # Initialize Slack notifier if not provided
        if slack_notifier is None:
            slack_notifier = SlackNotifier()
        
        # Search GitHub
        leaks = self.search_github_code(domain)
        
        # Save leaks to database and send immediate alerts
        for leak in leaks:
            leak["job_id"] = job_id
            leak["domain"] = domain
            save_leak(leak)
            
            # Send immediate Slack alert for CRITICAL/HIGH severity leaks
            if leak.get("severity") in ["critical", "high"]:
                slack_notifier.send_alert(
                    domain=domain,
                    threat_type="leak",
                    severity=leak["severity"].upper(),
                    details=leak
                )
        
        return leaks


def process_leak_job(job_data: Dict[str, Any]) -> None:
    """
    Process a leak detection job from the queue
    
    Args:
        job_data: Job payload from Redis
    """
    job_id = job_data.get("job_id")
    domain = job_data.get("domain")
    
    logger.info(f"Processing leak detection job {job_id} for domain: {domain}")
    
    try:
        # Update status to processing
        update_job_status(job_id, "processing")
        
        # Initialize hunter and Slack notifier
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.warning("⚠️ No GitHub token configured - scan will be limited")
        
        hunter = LeakHunter(github_token)
        slack_notifier = SlackNotifier()
        
        # Run scan (Slack alerts sent immediately for each critical leak)
        leaks = hunter.scan(domain, job_id, slack_notifier)
        
        # Send summary after scan completes
        if leaks:
            critical_count = sum(1 for l in leaks if l.get("severity") in ["critical", "high"])
            slack_notifier.send_summary(
                domain=domain,
                scan_type="leak",
                total_threats=len(leaks),
                critical_threats=critical_count
            )
        
        # Mark as completed
        update_job_status(job_id, "completed")
        logger.info(f"Job {job_id} completed successfully. Found {len(leaks)} leaks")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job_status(job_id, "failed", str(e))


def main():
    """Main worker loop"""
    logger.info("Leak detection worker started")
    
    redis_client = get_redis_connection()
    queue_name = "queue:leak"
    
    logger.info(f"Listening on queue: {queue_name}")
    
    while True:
        try:
            # Block and wait for jobs (BRPOP with 5 second timeout)
            result = redis_client.brpop(queue_name, timeout=5)
            
            if result:
                _, job_payload = result
                job_data = json.loads(job_payload)
                
                logger.info(f"Received job: {job_data}")
                process_leak_job(job_data)
            
        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    main()
