import React from 'react'

export default function PlayerCard({
    player,
    pos,
    isStarter,
    isBench,
    isCaptain,
    isVice,
    showActions,
    onOpen,
    onToggleStarter,
    onCaptain,
    onVice
}) {
    return (
        <div className='player-slot'>
            <div
                className={`player-slot-card ${isBench ? 'bench' : ''}`}
                onClick={onOpen}
            >
                {player ? (
                    <>
                        <div className='slot-name'>
                            {player.web_name}
                            {isCaptain && ' (C)'}
                            {isVice && ' (V)'}
                        </div>
                        <div className='slot-pts'>
                            {player.predicted_points.toFixed(1)}
                        </div>

                        {showActions && (
                            <div className='slot-actions'>
                                <button
                                    className={isStarter ? 'on' : ''}
                                    onClick={e => {
                                        e.stopPropagation()
                                        onToggleStarter()
                                    }}
                                >XI</button>
                                <button
                                    className={isCaptain ? 'on' : ''}
                                    onClick={e => {
                                        e.stopPropagation()
                                        onCaptain()
                                    }}
                                >C</button>
                                <button
                                    className={isVice ? 'on' : ''}
                                    onClick={e => {
                                        e.stopPropagation()
                                        onVice()
                                    }}
                                >V</button>
                            </div>
                        )}
                    </>
                ) : (
                    <>
                        <div className='slot-icon'>+</div>
                        <div className='slot-pos'>{pos}</div>
                    </>
                )}
            </div>
        </div>
    )
}