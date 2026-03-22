"""YouTube TV Channel Mappings Manager

Parses browse.json from YouTube TV's internal API to extract
channel name → videoId mappings for Roku deep linking.

Deep link format: POST http://<roku_ip>:8060/launch/195316?contentId=<videoId>&mediaType=live

Video IDs rotate every few months, so mappings need periodic refresh.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
MAPPINGS_FILE = os.path.join(CONFIG_DIR, 'ytv_channel_mappings.json')


class YTVChannelMapper:
    def __init__(self):
        self.mappings: Dict[str, str] = {}  # channel_name (uppercase) -> videoId
        self.updated_at: Optional[str] = None
        self._load_mappings()

    def _load_mappings(self):
        """Load saved mappings from disk."""
        try:
            if os.path.exists(MAPPINGS_FILE):
                with open(MAPPINGS_FILE, 'r') as f:
                    data = json.load(f)
                self.mappings = data.get('channels', {})
                self.updated_at = data.get('updated_at')
                logger.info(f"Loaded {len(self.mappings)} YouTube TV channel mappings (updated {self.updated_at})")
        except Exception as e:
            logger.error(f"Failed to load YTV channel mappings: {e}")

    def _save_mappings(self):
        """Save mappings to disk."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            data = {
                'channels': self.mappings,
                'updated_at': self.updated_at,
                'count': len(self.mappings)
            }
            with open(MAPPINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.mappings)} YouTube TV channel mappings")
        except Exception as e:
            logger.error(f"Failed to save YTV channel mappings: {e}")

    def parse_browse_json(self, browse_data: dict) -> int:
        """Parse YouTube TV browse.json response and extract channel→videoId mappings.

        JSON path:
          contents → epgRenderer → paginationRenderer → epgPaginationRenderer → contents[]
            → epgRowRenderer → station → epgStationRenderer → icon → accessibility
              → accessibilityData → label  (channel name)
            → epgRowRenderer → airings[0] → epgAiringRenderer → navigationEndpoint
              → watchEndpoint → videoId

        Fallback path for blocked/restricted broadcasts:
            → epgAiringRenderer → navigationEndpoint → unpluggedPopupEndpoint
              → popupRenderer → unpluggedSelectionMenuDialogRenderer → items[0]
              → unpluggedMenuItemRenderer → command → watchEndpoint → videoId

        Returns number of channels parsed.
        """
        new_mappings = {}

        try:
            # Navigate to the EPG contents array
            contents = (browse_data
                       .get('contents', {})
                       .get('epgRenderer', {})
                       .get('paginationRenderer', {})
                       .get('epgPaginationRenderer', {})
                       .get('contents', []))

            if not contents:
                logger.warning("No epgPaginationRenderer contents found in browse.json")
                return 0

            for channel_obj in contents:
                row = channel_obj.get('epgRowRenderer', {})
                if not row:
                    continue

                # Extract channel name
                channel_name = self._extract_channel_name(row)
                if not channel_name:
                    continue

                # Extract videoId
                video_id = self._extract_video_id(row)
                if not video_id:
                    continue

                new_mappings[channel_name.upper().strip()] = video_id.strip()

        except Exception as e:
            logger.error(f"Error parsing browse.json: {e}")
            return 0

        if new_mappings:
            self.mappings = new_mappings
            self.updated_at = datetime.now().isoformat()
            self._save_mappings()
            logger.info(f"Parsed {len(new_mappings)} channels from browse.json")

        return len(new_mappings)

    def _extract_channel_name(self, row: dict) -> Optional[str]:
        """Extract channel name from epgRowRenderer."""
        try:
            # Primary path: station → epgStationRenderer → icon → accessibility
            name = (row.get('station', {})
                      .get('epgStationRenderer', {})
                      .get('icon', {})
                      .get('accessibility', {})
                      .get('accessibilityData', {})
                      .get('label'))
            if name:
                return name

            # Fallback: station → epgStationRenderer → label
            name = (row.get('station', {})
                      .get('epgStationRenderer', {})
                      .get('label'))
            if name:
                return name

            # Fallback: direct label on the row
            return row.get('label')
        except Exception:
            return None

    def _extract_video_id(self, row: dict) -> Optional[str]:
        """Extract videoId from epgRowRenderer airings."""
        try:
            airings = row.get('airings', [])
            if not airings:
                return None

            airing = airings[0].get('epgAiringRenderer', {})
            nav = airing.get('navigationEndpoint', {})

            # Primary path: watchEndpoint → videoId
            video_id = nav.get('watchEndpoint', {}).get('videoId')
            if video_id:
                return video_id

            # Fallback path for blocked/restricted broadcasts
            video_id = (nav.get('unpluggedPopupEndpoint', {})
                          .get('popupRenderer', {})
                          .get('unpluggedSelectionMenuDialogRenderer', {})
                          .get('items', [{}])[0]
                          .get('unpluggedMenuItemRenderer', {})
                          .get('command', {})
                          .get('watchEndpoint', {})
                          .get('videoId'))
            return video_id
        except Exception:
            return None

    def get_video_id(self, channel_name: str) -> Optional[str]:
        """Look up videoId for a channel name. Case-insensitive, fuzzy matching."""
        name = channel_name.upper().strip()

        # Exact match
        if name in self.mappings:
            return self.mappings[name]

        # Try common variations
        for stored_name, video_id in self.mappings.items():
            # Without spaces/special chars (e.g., "ESPN NEWS" matches "ESPNEWS")
            if name.replace(' ', '') == stored_name.replace(' ', ''):
                return video_id

        for stored_name, video_id in self.mappings.items():
            # Substring match (e.g., "ESPN" matches "ESPN HD")
            if name in stored_name or stored_name in name:
                return video_id

        return None

    def get_all_mappings(self) -> dict:
        """Return all mappings with metadata."""
        return {
            'channels': self.mappings,
            'count': len(self.mappings),
            'updated_at': self.updated_at
        }

    def mark_stale(self, channel_name: str):
        """Mark a specific channel's videoId as stale (remove it)."""
        name = channel_name.upper().strip()
        if name in self.mappings:
            old_id = self.mappings.pop(name)
            self._save_mappings()
            logger.warning(f"Marked {name} videoId as stale (was {old_id})")


# Singleton instance
_mapper: Optional[YTVChannelMapper] = None

def get_mapper() -> YTVChannelMapper:
    global _mapper
    if _mapper is None:
        _mapper = YTVChannelMapper()
    return _mapper
