import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getTopPlayers } from '../services/api'

const posColors = {
    'GK': '#f5a623',
    'DEF': '#00ff87',
    'MID': '#04f5ff',
    'FWD': '#e90052'
}

export default function Home() {
    const [topPlayers, setTopPlayers] = useState(null)
    const gw = 8

    useEffect(() => {
        getTopPlayers(gw)
            .then(res => setTopPlayers(res.data))
            .catch(err => console.log(err))
    }, [])

    if (!topPlayers) return <div className='loading'>Loading...</div>

    return (
        <div className='home'>

        
            <div className='hero'>
                <div className='hero-overlay'>
                    <h1>FPL PREDICTOR</h1>
                    <p>AI-powered Fantasy Premier League predictions</p>
                    <div className='hero-buttons'>
                        <Link to="/squad" className='btn-primary'>Build Your Team</Link>
                        <Link to="/squad" className='btn-secondary'>Get Best Team</Link>
                    </div>
                </div>
            </div>

          
            <div className='gw-section'>
                <h2>GAMEWEEK {gw} TOP PICKS</h2>
                <p className='gw-subtitle'>Our AI predictions for this gameweek</p>

                <div className='top-picks'>
                    {['GK', 'DEF', 'MID', 'FWD'].map(pos => {
                        const player = topPlayers[pos][0]
                        return (
                            <div key={pos} className='player-card'>
                                <div className='player-avatar' style={{ backgroundColor: posColors[pos] }}>
                                    <span>{player.web_name.charAt(0)}</span>
                                </div>
                                <div className='pos-badge' style={{ backgroundColor: posColors[pos] }}>
                                    {pos}
                                </div>
                                <h3>{player.web_name}</h3>
                                <p className='team-name'>{player.team_name}</p>
                                <p className='opponent'>vs {player.opponent}</p>
                                <div className='card-stats'>
                                    <div className='stat'>
                                        <span className='stat-value'>£{player.price}m</span>
                                        <span className='stat-label'>Price</span>
                                    </div>
                                    <div className='stat'>
                                        <span className='stat-value'>{player.predicted_points.toFixed(1)}</span>
                                        <span className='stat-label'>Pred. Pts</span>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

          
            <div className='cta-section'>
                <div className='cta-card'>
                    <h3> Build & Evaluate Your Team</h3>
                    <p>Pick your 15 players and see how your squad scores against our AI predictions</p>
                    <Link to="/squad" className='btn-primary'>Evaluate My Team</Link>
                </div>
                <div className='cta-card'>
                    <h3>Get AI Best Team</h3>
                    <p>Let our AI optimizer pick the best possible squad within your £100m budget</p>
                    <Link to="/squad" className='btn-secondary'>Get Best Team</Link>
                </div>
            </div>

            
            <footer className='footer'>
                <div className='footer-content'>
                    <div className='footer-brand'>
                        <h2>FPL Predictor</h2>
                        <p>AI-powered Fantasy Premier League predictions</p>
                    </div>
                    <div className='footer-links'>
                        <h4>Navigation</h4>
                        <Link to="/">Home</Link>
                        <Link to="/squad">Squad Builder</Link>
                    </div>
                    <div className='footer-links'>
                        <h4>Info</h4>
                        <a href="#">About</a>
                        <a href="#">Contact</a>
                    </div>
                </div>
                <div className='footer-bottom'>
                    <p>© 2026 FPL Predictor. Built with AI </p>
                </div>
            </footer>

        </div>
    )
}