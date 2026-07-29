import { useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'

export default function ChartCanvas({ config }) {
    const canvasRef = useRef(null)
    const chartRef = useRef(null)

    useEffect(() => {
        chartRef.current = new Chart(canvasRef.current, config)
        return () => {
            chartRef.current.destroy()
        }
    }, [config])

    return (
        <div className="chart-box">
            <canvas ref={canvasRef}></canvas>
        </div>
    )
}
