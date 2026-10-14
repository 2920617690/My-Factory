import { Pause, Play, RotateCcw, SkipForward } from 'lucide-react'

import { timelineMarks } from '../simulationData'

interface TimelineControlsProps {
  playhead: number
  playing: boolean
  onPlayToggle: () => void
  onStep: () => void
  onReset: () => void
  onPlayheadChange: (value: number) => void
}

export function TimelineControls({
  playhead,
  playing,
  onPlayToggle,
  onStep,
  onReset,
  onPlayheadChange,
}: TimelineControlsProps) {
  return (
    <section className="panel timeline-panel">
      <div className="timeline-row">
        <button type="button" className="icon-button" onClick={onPlayToggle} title={playing ? '暂停' : '播放'}>
          {playing ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <button type="button" className="icon-button" onClick={onStep} title="单步">
          <SkipForward size={18} />
        </button>
        <button type="button" className="icon-button" onClick={onReset} title="重置">
          <RotateCcw size={18} />
        </button>
        <div className="timeline-track">
          <input
            aria-label="仿真时间"
            type="range"
            min="0"
            max="12"
            step="1"
            value={playhead}
            onChange={(event) => onPlayheadChange(Number(event.target.value))}
          />
          <div className="timeline-marks" aria-hidden="true">
            {timelineMarks.map((mark) => (
              <span key={mark}>时刻 {mark}</span>
            ))}
          </div>
        </div>
        <output>{playhead} 分钟</output>
      </div>
    </section>
  )
}


