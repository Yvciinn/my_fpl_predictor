import React, { useState, useEffect } from 'react'
import { getAllPlayers, getBestTeam } from '../services/api'
import PlayerCard from '../assets/PlayerCard'
import ChatBot from '../assets/ChatBot'


const normalize = (str = '') =>
    String(str ?? '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/ø/g, 'o')
        .replace(/ß/g, 'ss')


const CAPTAIN_DOUBLED = true

export default function SquadBuilder() {
    const GW = 8

    const [squad, setSquad] = useState({
        GK:  [null, null],
        DEF: [null, null, null, null, null],
        MID: [null, null, null, null, null],
        FWD: [null, null, null]
    })
    const [starterIds, setStarterIds] = useState([])
    const [captainId, setCaptainId] = useState(null)
    const [viceId, setViceId] = useState(null)

    const [selectedSlot, setSelectedSlot] = useState(null)
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [allPlayers, setAllPlayers] = useState([])

    const [rating, setRating] = useState(null)
    const [loadingRating, setLoadingRating] = useState(false)

    // load all players once
    useEffect(() => {
        getAllPlayers(GW)
            .then(res => setAllPlayers(res.data))
            .catch(err => console.log('Error:', err))
    }, [])


    const picked = Object.values(squad).flat().filter(Boolean)
    const squadComplete = picked.length === 15
    const starters = picked.filter(p => starterIds.includes(p.player_id))
    const countPos = (pos) => starters.filter(p => p.pos_label === pos).length


    const formationValid =
        starters.length === 11 &&
        countPos('GK') === 1 &&
        countPos('DEF') >= 3 &&
        countPos('MID') >= 2 &&
        countPos('FWD') >= 1

    const ready =
        squadComplete &&
        formationValid &&
        captainId !== null &&
        viceId !== null &&
        captainId !== viceId

    const handleSearch = (e) => {
        const query = e.target.value
        setSearchQuery(query)

        const words = normalize(query).split(/\s+/).filter(Boolean)
        if (normalize(query).length < 2) {
            setSearchResults([])
            return
        }

        const filtered = allPlayers
            .filter(p => {
                if (p.pos_label !== selectedSlot.pos) return false
                // works now with web_name only; first_name / second_name are used once you add them
                const fullName = normalize(`${p.first_name ?? ''} ${p.second_name ?? ''} ${p.web_name}`)
                return words.every(w => fullName.includes(w))
            })
            .slice(0, 8)

        setSearchResults(filtered)
    }

  
    const selectPlayer = (player) => {
        if (picked.some(p => p.player_id === player.player_id)) {
            alert('Player already in your squad')
            return
        }

        const old = squad[selectedSlot.pos][selectedSlot.index]
        if (old) {
            setStarterIds(ids => ids.filter(x => x !== old.player_id))
            if (captainId === old.player_id) setCaptainId(null)
            if (viceId === old.player_id) setViceId(null)
        }

        setSquad(prev => ({
            ...prev,
            [selectedSlot.pos]: prev[selectedSlot.pos].map((p, i) =>
                i === selectedSlot.index ? player : p
            )
        }))
        setRating(null)
        setSelectedSlot(null)
        setSearchQuery('')
        setSearchResults([])
    }

    const toggleStarter = (id) => {
        if (starterIds.includes(id)) {
            setStarterIds(starterIds.filter(x => x !== id))
            if (captainId === id) setCaptainId(null)  
            if (viceId === id) setViceId(null)
        } else if (starterIds.length < 11) {
            setStarterIds([...starterIds, id])
        }
        setRating(null)
    }

    const chooseCaptain = (id) => {
        if (!starterIds.includes(id)) return
        if (viceId === id) setViceId(null)            
        setCaptainId(id)
        setRating(null)
    }

    const chooseVice = (id) => {
        if (!starterIds.includes(id)) return
        if (captainId === id) setCaptainId(null)
        setViceId(id)
        setRating(null)
    }

    const handleRate = async () => {
        try {
            setLoadingRating(true)
            const res = await getBestTeam(GW)
            const bestPts = res.data.summary.total_predicted_points

            let yourPts = starters.reduce((sum, p) => sum + p.predicted_points, 0)
            if (CAPTAIN_DOUBLED) {
                const captain = starters.find(p => p.player_id === captainId)
                yourPts += captain.predicted_points
            }

            const percent = Math.min((yourPts / bestPts) * 100, 100)

            setRating({
                yourPts: yourPts.toFixed(1),
                bestPts: bestPts.toFixed(1),
                percent: percent.toFixed(1)
            })
        } catch (err) {
            console.log('Rating error:', err)
        } finally {
            setLoadingRating(false)
        }
    }


    return (
        <div className='squad-builder'>
            <h2>Squad Builder</h2>

            <div className='squad-summary'>
                <p>Players: {picked.length}/15</p>
            </div>

            <div className='pitch'>
                {['FWD', 'MID', 'DEF', 'GK'].map(pos => (
                    <div key={pos} className='pitch-row'>
                        {squad[pos].map((player, i) => {
                            const isStarter = !!player && starterIds.includes(player.player_id)
                            const isBench =
                                !!player && squadComplete && starterIds.length > 0 && !isStarter

                            return (
                                <PlayerCard
                                    key={i}
                                    player={player}
                                    pos={pos}
                                    isStarter={isStarter}
                                    isBench={isBench}
                                    isCaptain={!!player && captainId === player.player_id}
                                    isVice={!!player && viceId === player.player_id}
                                    showActions={squadComplete}
                                    onOpen={() => {
                                        setSelectedSlot({ pos, index: i })
                                        setSearchQuery('')
                                        setSearchResults([])
                                    }}
                                    onToggleStarter={() => toggleStarter(player.player_id)}
                                    onCaptain={() => chooseCaptain(player.player_id)}
                                    onVice={() => chooseVice(player.player_id)}
                                />
                            )
                        })}
                    </div>
                ))}
            </div>

            {squadComplete && (
                <div className='lineup-status'>
                    <p>
                        Starters: {starters.length}/11
                        {starters.length === 11 && !formationValid && ' - invalid formation'}
                    </p>
                    <p>
                        Captain: {captainId ? '✓' : '✗'} · Vice: {viceId ? '✓' : '✗'}
                    </p>
                </div>
            )}

            <button
                className='rate-btn'
                disabled={!ready || loadingRating}
                onClick={handleRate}
            >
                {loadingRating ? 'Calculating...' : 'Rate'}
            </button>

            {rating && (
                <div className='rating-result'>
                    <h3>{rating.percent}%</h3>
                    <p>Your squad: {rating.yourPts} pts</p>
                    <p>Best AI team: {rating.bestPts} pts</p>
                </div>
            )}

            {selectedSlot && (
                <div className='popup-overlay' onClick={() => setSelectedSlot(null)}>
                    <div className='popup' onClick={e => e.stopPropagation()}>
                        <h3>Select {selectedSlot.pos}</h3>
                        <input
                            type='text'
                            placeholder='Search for a player...'
                            className='search-input'
                            autoFocus
                            value={searchQuery}
                            onChange={handleSearch}
                        />
                        <div className='search-results'>
                            {searchQuery.length >= 2 && searchResults.length === 0 && (
                                <p style={{ color: '#888', padding: '10px' }}>No players found</p>
                            )}
                            {searchResults.map(player => (
                                <div
                                    key={player._id}
                                    className='result-item'
                                    onClick={() => selectPlayer(player)}
                                >
                                    <div className='result-info'>
                                        <span className='result-name'>{player.web_name}</span>
                                        <span className='result-team'>{player.team_name}</span>
                                    </div>
                                    <div className='result-stats'>
                                        <span className='result-price'>£{player.price}m</span>
                                        <span className='result-pts'>
                                            {player.predicted_points.toFixed(1)} pts
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <ChatBot squadIds={picked.map(p => Number(p.player_id))} />
        </div>
    )
}