import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import '../styles/SportsScoreboard.css';

const LEAGUES = ['All', 'NHL', 'NBA', 'MLB', 'NFL', 'NCAAM', 'NCAAF'];
const LEAGUE_PARAM = { 'All': null, 'NHL': 'nhl', 'NBA': 'nba', 'MLB': 'mlb', 'NFL': 'nfl', 'NCAAM': 'ncaam', 'NCAAF': 'ncaaf' };
const STATUS_LABELS = { 'all': 'All Games', 'live': '🔴 Live', 'upcoming': 'Upcoming', 'final': 'Final' };
const REFRESH_INTERVAL = 60000; // 60 seconds

const SportsScoreboard = ({ selectedTV, onLaunchApp, tvs, onGameLaunched }) => {
  const [games, setGames] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedLeague, setSelectedLeague] = useState('All');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchGames = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const params = new URLSearchParams();
      const sportParam = LEAGUE_PARAM[selectedLeague];
      if (sportParam) params.set('sport', sportParam);
      if (statusFilter !== 'all') params.set('status', statusFilter);

      const response = await axios.get(`/api/sports/games?${params}`);
      setGames(response.data.games || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching sports games:', err);
      setError('Failed to load sports games');
    } finally {
      setIsLoading(false);
    }
  }, [selectedLeague, statusFilter]);

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  // Auto-refresh for live games
  useEffect(() => {
    const interval = setInterval(fetchGames, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchGames]);

  const handleLaunchGame = async (game, app, tvId) => {
    if (!tvId) {
      alert('Please select a TV first');
      return;
    }

    try {
      // MLB games: launch MLB app on Fire TV and navigate to specific game
      if (app.app_name === 'MLB') {
        await axios.post('/api/tv/launch-mlb', {
          tv_id: tvId,
          away_team: game.away_team.short_name,
          home_team: game.home_team.short_name,
          mlb_game_pk: game.mlb_game_pk || null,
          title: `${game.away_team.name} vs ${game.home_team.name}`
        });
      // ESPN+ games: launch ESPN app on Fire TV and navigate to specific game
      } else if (app.app_name === 'ESPN+' || app.app_name === 'ESPN') {
        await axios.post('/api/tv/launch-espn', {
          tv_id: tvId,
          away_team: game.away_team.short_name,
          home_team: game.home_team.short_name,
          espn_id: game.espn_id || null,
          title: `${game.away_team.name} vs ${game.home_team.name}`
        });
      // Peacock / Amazon Prime: just launch the app on Roku (no game navigation)
      } else if (app.app_name === 'Peacock' || app.app_name === 'Prime Video' || app.app_name === 'Amazon Prime') {
        const serviceName = app.app_name === 'Amazon Prime' ? 'Prime Video' : app.app_name;
        await axios.post('/api/tv/launch', {
          tv_id: tvId,
          content_id: 'home',
          title: `${game.away_team.name} vs ${game.home_team.name}`,
          service: serviceName
        });
      // YouTube TV broadcasts: tune to the channel via Fire TV (Cobalt deep link)
      } else if (app.app_name === 'YouTubeTV' && app.broadcast_name) {
        await axios.post('/api/tv/tune', {
          tv_id: tvId,
          channel: app.broadcast_name
        });
      } else {
        await axios.post('/api/tv/launch', {
          tv_id: tvId,
          content_id: game.id,
          title: `${game.away_team.name} vs ${game.home_team.name}`,
          service: app.app_name
        });
      }

      const tvName = tvs?.find(t => t.id === tvId)?.name || tvId;
      const gameTitle = `${game.away_team.short_name} vs ${game.home_team.short_name}`;
      if (onGameLaunched) {
        onGameLaunched(tvId, app.app_name, gameTitle);
      }
      alert(`Launching ${app.app_name} on ${tvName}!`);
    } catch (err) {
      console.error('Error launching game:', err);
      alert(`Failed to launch ${app.app_name}`);
    }
  };

  const getStatusBadge = (status, detail) => {
    switch (status) {
      case 'in':
        return <span className="status-badge live">🔴 LIVE &mdash; {detail}</span>;
      case 'pre':
        return <span className="status-badge upcoming">🟡 {detail}</span>;
      case 'post':
        return <span className="status-badge final">✅ {detail}</span>;
      default:
        return <span className="status-badge">{detail}</span>;
    }
  };

  const liveCount = games.filter(g => g.status === 'in').length;

  return (
    <div className="sports-scoreboard">
      <div className="sports-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h2>
          🏟️ Live Sports
          {liveCount > 0 && <span className="live-count">{liveCount} Live</span>}
        </h2>
        <div className="sports-header-right">
          {lastUpdated && (
            <span className="last-updated">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button className="collapse-btn" onClick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }}>
            {isCollapsed ? '▼ Show' : '▲ Hide'}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          <div className="sports-filters">
            <div className="league-tabs">
              {LEAGUES.map(league => (
                <button
                  key={league}
                  className={`league-tab ${selectedLeague === league ? 'active' : ''}`}
                  onClick={() => setSelectedLeague(league)}
                >
                  {league}
                </button>
              ))}
            </div>
            <div className="status-tabs">
              {Object.entries(STATUS_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  className={`status-tab ${statusFilter === key ? 'active' : ''}`}
                  onClick={() => setStatusFilter(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="sports-error">{error}</div>}

          {isLoading && games.length === 0 ? (
            <div className="sports-loading">Loading games...</div>
          ) : games.length === 0 ? (
            <div className="sports-empty">No games found for the selected filters.</div>
          ) : (
            <div className="games-grid">
              {games.map((game) => (
                <div key={game.id} className={`game-card ${game.status === 'in' ? 'live-game' : ''}`}>
                  <div className="game-league-badge">{game.league}</div>

                  <div className="game-teams">
                    <div className="team away-team">
                      {game.away_team.logo && (
                        <img src={game.away_team.logo} alt={game.away_team.short_name} className="team-logo" />
                      )}
                      <div className="team-info">
                        <span className="team-name">{game.away_team.short_name}</span>
                        <span className="team-record">{game.away_team.record}</span>
                      </div>
                      {(game.status === 'in' || game.status === 'post') && (
                        <span className="team-score">{game.away_team.score}</span>
                      )}
                    </div>

                    <div className="game-vs">
                      {game.status === 'in' || game.status === 'post' ? '' : '@'}
                    </div>

                    <div className="team home-team">
                      {game.home_team.logo && (
                        <img src={game.home_team.logo} alt={game.home_team.short_name} className="team-logo" />
                      )}
                      <div className="team-info">
                        <span className="team-name">{game.home_team.short_name}</span>
                        <span className="team-record">{game.home_team.record}</span>
                      </div>
                      {(game.status === 'in' || game.status === 'post') && (
                        <span className="team-score">{game.home_team.score}</span>
                      )}
                    </div>
                  </div>

                  <div className="game-status">
                    {getStatusBadge(game.status, game.status_detail)}
                  </div>

                  <div className="game-broadcast">
                    📺 {game.broadcast_display}
                  </div>

                  <div className="game-actions">
                    {game.watchable_apps && game.watchable_apps.map((app) => (
                      <div key={app.app_name} className="watch-action">
                        {selectedTV ? (
                          <button
                            className="watch-btn"
                            onClick={() => handleLaunchGame(game, app, selectedTV.id)}
                            title={`Launch ${app.app_name} on ${selectedTV.name}`}
                          >
                            ▶ Watch on {app.app_name}
                          </button>
                        ) : tvs && tvs.length > 0 ? (
                          <div className="tv-launch-group">
                            <span className="watch-label">{app.app_name}:</span>
                            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'3px'}}>
                              {['upper_left','upper_right','lower_left','lower_right'].map(tvId => {
                                const tv = tvs.find(t => t.id === tvId);
                                if (!tv) return <span key={tvId} />;
                                const label = {upper_left:'UL',upper_right:'UR',lower_left:'LL',lower_right:'LR'}[tvId];
                                return (
                                  <button
                                    key={tv.id}
                                    className="watch-btn-sm"
                                    onClick={() => handleLaunchGame(game, app, tv.id)}
                                    title={`Launch ${app.app_name} on ${tv.name}`}
                                  >
                                    {label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        ) : (
                          <span className="watch-label">Watch on {app.app_name}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SportsScoreboard;
