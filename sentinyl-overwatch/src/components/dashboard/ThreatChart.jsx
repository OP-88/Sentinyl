import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp } from 'lucide-react';

/**
 * ThreatChart - Threats detected over time
 * 
 * Line chart showing trend analysis for security threats
 */
export default function ThreatChart() {
    // Mock data for last 7 days
    const data = [
        { date: 'Dec 13', threats: 45, critical: 3 },
        { date: 'Dec 14', threats: 52, critical: 5 },
        { date: 'Dec 15', threats: 38, critical: 2 },
        { date: 'Dec 16', threats: 61, critical: 7 },
        { date: 'Dec 17', threats: 73, critical: 4 },
        { date: 'Dec 18', threats: 55, critical: 6 },
        { date: 'Dec 19', threats: 89, critical: 8 }
    ];

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                    <p className="text-white font-semibold mb-2">{payload[0].payload.date}</p>
                    <p className="text-cyan-400 text-sm">
                        Total Threats: <span className="font-bold">{payload[0].value}</span>
                    </p>
                    <p className="text-red-400 text-sm">
                        Critical: <span className="font-bold">{payload[1].value}</span>
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">Threat Trends</h2>
                <div className="flex items-center gap-2 text-green-400">
                    <TrendingUp className="w-5 h-5" />
                    <span className="text-sm font-medium">Last 7 days</span>
                </div>
            </div>

            <ResponsiveContainer width="100%" height={250}>
                <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: 12 }} />
                    <YAxis stroke="#94a3b8" style={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line
                        type="monotone"
                        dataKey="threats"
                        stroke="#06b6d4"
                        strokeWidth={2}
                        dot={{ fill: '#06b6d4', r: 4 }}
                        activeDot={{ r: 6 }}
                        name="Total Threats"
                    />
                    <Line
                        type="monotone"
                        dataKey="critical"
                        stroke="#ef4444"
                        strokeWidth={2}
                        dot={{ fill: '#ef4444', r: 4 }}
                        activeDot={{ r: 6 }}
                        name="Critical"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
