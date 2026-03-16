#!/usr/bin/env python3
"""
YouTube TV API Key Validation Test Harness

Tests the YouTube API key and validates:
- API key format and configuration
- Authentication with Google
- Search functionality
- Response structure and validity
- API quota and rate limits
"""

import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv


class YouTubeAPITester:
    """Test harness for YouTube TV API key validation"""

    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_TV_API_KEY', '').strip()
        self.base_url = 'https://www.googleapis.com/youtube/v3'
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'info': []
        }
        self.test_queries = [
            'breaking bad',
            'stranger things',
            'game of thrones',
            'the office',
            'test query 12345'
        ]

    def print_header(self, text: str) -> None:
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")

    def print_test(self, status: str, test_name: str, details: str = '') -> None:
        """Print a test result"""
        symbols = {
            'PASS': '✅',
            'FAIL': '❌',
            'WARN': '⚠️ ',
            'INFO': 'ℹ️ '
        }
        symbol = symbols.get(status, '  ')
        print(f"{symbol} [{status:5s}] {test_name}")
        if details:
            print(f"         {details}")

    def test_api_key_format(self) -> bool:
        """Test 1: Validate API key format"""
        self.print_header("TEST 1: API Key Configuration")

        if not self.api_key:
            self.print_test('FAIL', 'API Key Present', 'YOUTUBE_TV_API_KEY not set in .env')
            self.results['failed'].append('API key not configured')
            return False

        self.print_test('PASS', 'API Key Present', f'Key starts with: {self.api_key[:10]}...')

        if self.api_key == 'your_youtube_tv_api_key_here':
            self.print_test('FAIL', 'API Key Valid', 'Using placeholder value')
            self.results['failed'].append('API key is placeholder')
            return False

        self.print_test('PASS', 'API Key Valid', 'Not using placeholder')
        self.results['passed'].append('API key is properly configured')
        return True

    def test_api_key_length(self) -> bool:
        """Test 2: Validate API key length"""
        self.print_header("TEST 2: API Key Format Validation")

        # Google API keys are typically 39 characters
        if len(self.api_key) < 30:
            self.print_test('WARN', 'API Key Length', f'Key length is {len(self.api_key)} (expected ~39)')
            self.results['warnings'].append('API key length seems short')
            return False

        self.print_test('PASS', 'API Key Length', f'Key length: {len(self.api_key)} characters')
        self.results['passed'].append('API key has valid length')
        return True

    async def test_authentication(self) -> bool:
        """Test 3: Authenticate with Google API"""
        self.print_header("TEST 3: Google Authentication")

        try:
            async with aiohttp.ClientSession() as session:
                # Try a simple search to authenticate
                url = f"{self.base_url}/search"
                params = {
                    'q': 'test',
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': 1,
                    'key': self.api_key
                }

                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    data = await response.json()

                    if response.status == 200:
                        self.print_test('PASS', 'Authentication Success', f'Status code: {response.status}')
                        self.results['passed'].append('Successfully authenticated with YouTube API')
                        return True

                    elif response.status == 400:
                        error = data.get('error', {}).get('message', 'Unknown error')
                        self.print_test('FAIL', 'Authentication Failed', f'Invalid request: {error}')
                        self.results['failed'].append(f'API request error: {error}')
                        return False

                    elif response.status == 401:
                        self.print_test('FAIL', 'Authentication Failed', 'Invalid or expired API key')
                        self.results['failed'].append('API key is invalid or expired')
                        return False

                    elif response.status == 403:
                        error = data.get('error', {}).get('message', 'Unknown error')
                        self.print_test('FAIL', 'Permission Denied', f'API not enabled or quota exceeded: {error}')
                        self.results['failed'].append('API permission denied - check if YouTube Data API v3 is enabled')
                        return False

                    elif response.status == 429:
                        self.print_test('WARN', 'Rate Limited', 'API quota exceeded - try again later')
                        self.results['warnings'].append('Rate limited by Google API')
                        return False

                    else:
                        self.print_test('FAIL', 'Authentication Failed', f'Unexpected status: {response.status}')
                        print(f"Response: {json.dumps(data, indent=2)}")
                        return False

        except asyncio.TimeoutError:
            self.print_test('FAIL', 'Authentication Failed', 'Request timeout - network issue')
            self.results['failed'].append('API request timed out')
            return False
        except Exception as e:
            self.print_test('FAIL', 'Authentication Failed', f'Exception: {str(e)}')
            self.results['failed'].append(f'Network error: {str(e)}')
            return False

    async def test_search_functionality(self) -> bool:
        """Test 4: Test actual search functionality"""
        self.print_header("TEST 4: Search Functionality")

        successful_searches = 0

        for query in self.test_queries[:3]:  # Test first 3 queries
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/search"
                    params = {
                        'q': query,
                        'part': 'snippet',
                        'type': 'video',
                        'maxResults': 5,
                        'key': self.api_key,
                        'relevanceLanguage': 'en'
                    }

                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('items', [])
                            self.print_test('PASS', f'Search: "{query}"', f'Found {len(items)} results')
                            successful_searches += 1

                            # Validate response structure
                            if items:
                                first_item = items[0]
                                has_title = 'snippet' in first_item and 'title' in first_item['snippet']
                                has_video_id = 'id' in first_item and 'videoId' in first_item['id']
                                has_thumbnail = 'snippet' in first_item and 'thumbnails' in first_item['snippet']

                                if has_title and has_video_id and has_thumbnail:
                                    self.print_test('PASS', f'  Response Structure', 'Valid (has title, ID, thumbnail)')
                                else:
                                    self.print_test('WARN', f'  Response Structure', 'Missing some expected fields')
                        else:
                            self.print_test('FAIL', f'Search: "{query}"', f'Status code: {response.status}')

            except Exception as e:
                self.print_test('FAIL', f'Search: "{query}"', f'Exception: {str(e)}')

        if successful_searches == 3:
            self.results['passed'].append('All test searches successful')
            return True
        elif successful_searches > 0:
            self.print_test('WARN', 'Partial Success', f'{successful_searches}/3 searches succeeded')
            self.results['warnings'].append(f'Only {successful_searches}/3 test searches succeeded')
            return True
        else:
            self.results['failed'].append('No successful searches')
            return False

    async def test_response_quality(self) -> bool:
        """Test 5: Validate response quality and completeness"""
        self.print_header("TEST 5: Response Quality & Completeness")

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/search"
                params = {
                    'q': 'breaking bad',
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': 10,
                    'key': self.api_key
                }

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        self.print_test('FAIL', 'Response Quality', f'Bad status: {response.status}')
                        return False

                    data = await response.json()
                    items = data.get('items', [])

                    if len(items) < 5:
                        self.print_test('WARN', 'Result Count', f'Got only {len(items)} results (expected 10)')
                        self.results['warnings'].append(f'Search returned {len(items)} results instead of requested 10')
                    else:
                        self.print_test('PASS', 'Result Count', f'Got {len(items)} results as expected')

                    # Check each result has expected fields
                    complete_count = 0
                    for i, item in enumerate(items[:5]):
                        required_fields = {
                            'id.videoId': item.get('id', {}).get('videoId'),
                            'snippet.title': item.get('snippet', {}).get('title'),
                            'snippet.description': item.get('snippet', {}).get('description'),
                            'snippet.thumbnails': item.get('snippet', {}).get('thumbnails')
                        }

                        if all(required_fields.values()):
                            complete_count += 1

                    self.print_test('PASS', 'Field Completeness', f'{complete_count}/5 items have all required fields')
                    if complete_count == 5:
                        self.results['passed'].append('All search results complete')
                    else:
                        self.results['warnings'].append(f'Only {complete_count}/5 results have complete data')

                    return True

        except Exception as e:
            self.print_test('FAIL', 'Response Quality', f'Exception: {str(e)}')
            return False

    async def test_api_limits(self) -> bool:
        """Test 6: Check API quota/limits"""
        self.print_header("TEST 6: API Quota & Limits")

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/search"
                params = {
                    'q': 'test',
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': 1,
                    'key': self.api_key
                }

                async with session.get(url, params=params) as response:
                    # Check for quota headers
                    if response.status == 200:
                        self.print_test('PASS', 'Quota Status', 'API responding normally')
                        self.results['passed'].append('API quota appears available')
                        return True
                    elif response.status == 429:
                        self.print_test('FAIL', 'Quota Exceeded', 'API rate limit reached')
                        self.results['failed'].append('API quota exceeded')
                        return False
                    elif response.status == 403:
                        data = await response.json()
                        error_msg = data.get('error', {}).get('message', 'Unknown')
                        if 'quota' in error_msg.lower():
                            self.print_test('FAIL', 'Quota Exceeded', error_msg)
                            self.results['failed'].append('API quota exceeded')
                            return False

                    self.print_test('PASS', 'Quota Status', 'No quota issues detected')
                    return True

        except Exception as e:
            self.print_test('WARN', 'Quota Check', f'Could not verify quota: {str(e)}')
            return True

    def print_summary(self) -> None:
        """Print test summary"""
        self.print_header("TEST SUMMARY")

        passed_count = len(self.results['passed'])
        failed_count = len(self.results['failed'])
        warning_count = len(self.results['warnings'])

        print(f"✅ Passed:  {passed_count}")
        print(f"❌ Failed:  {failed_count}")
        print(f"⚠️  Warnings: {warning_count}\n")

        if self.results['passed']:
            print("Passed Tests:")
            for test in self.results['passed']:
                print(f"  ✅ {test}")

        if self.results['failed']:
            print("\nFailed Tests:")
            for test in self.results['failed']:
                print(f"  ❌ {test}")

        if self.results['warnings']:
            print("\nWarnings:")
            for test in self.results['warnings']:
                print(f"  ⚠️  {test}")

        # Overall status
        print(f"\n{'='*60}")
        if failed_count == 0 and warning_count == 0:
            print("🎉 All tests passed! YouTube TV API is working perfectly!")
            print(f"{'='*60}\n")
            return True
        elif failed_count == 0:
            print("✅ API is functional with some minor warnings")
            print(f"{'='*60}\n")
            return True
        else:
            print("❌ API validation failed - see errors above")
            print(f"{'='*60}\n")
            return False

    async def run_all_tests(self) -> bool:
        """Run all tests"""
        print("\n")
        print("╔" + "="*58 + "╗")
        print("║" + " "*58 + "║")
        print("║" + "  YouTube TV API Key Validation Test Harness".center(58) + "║")
        print("║" + f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(58) + "║")
        print("║" + " "*58 + "║")
        print("╚" + "="*58 + "╝")

        # Run tests
        test1_pass = self.test_api_key_format()
        test2_pass = self.test_api_key_length()
        test3_pass = await self.test_authentication()
        test4_pass = await self.test_search_functionality() if test3_pass else False
        test5_pass = await self.test_response_quality() if test4_pass else False
        test6_pass = await self.test_api_limits() if test3_pass else False

        # Print summary
        summary_pass = self.print_summary()

        return summary_pass


async def main():
    """Main entry point"""
    # Load .env file
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print(f"Warning: .env file not found at {env_file}")

    tester = YouTubeAPITester()
    success = await tester.run_all_tests()

    # Next steps
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)

    if success and len(tester.results['failed']) == 0:
        print("""
✅ Your YouTube TV API key is valid and working!

You can now:
  1. Use the web UI at http://localhost:3000 to search
  2. The YouTube TV searches will use REAL data from YouTube
  3. Add more streaming service credentials to .env
  4. Test voice commands through the Sonos integration
        """)
    else:
        print("""
❌ There are issues with your YouTube TV API key.

To fix it:
  1. Go to https://console.cloud.google.com/
  2. Make sure YouTube Data API v3 is ENABLED
  3. Check that your API key has the right permissions
  4. Verify the key in .env matches exactly
  5. Run this test again: python test_youtube_api.py

Common issues:
  - API key has wrong format
  - YouTube Data API v3 not enabled in Google Cloud
  - API key quota exceeded
  - API key restricted to wrong hosts
        """)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
