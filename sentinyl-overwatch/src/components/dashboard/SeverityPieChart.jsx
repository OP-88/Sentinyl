import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Shield } from 'lucide-react';

/**
 * SeverityPieChart - Threat severity breakdown
 * 
 * Pie chart showing distribution of threats by severity level
 */
export default function SeverityPieChart() {
    const data = [
        { name: 'Critical', value: 23, color: '#ef4444' },
        { name: 'High', value: 87, color: '#f97316' },
        { name: 'Medium', value: 104, color: '#eab308' },
        { name: 'Low', value: 33, color: '#3b82f6' }
    ];

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0];
            return (
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                    <p className="text-white font-semibold mb-1">{data.name}</p>
                    <p className="text-slate-400 text-sm">
                        Count: <span className="font-bold" style={{ color: data.payload.color }}>{data.value}</span>
                    </p>
                </div>
            );
        }
        return null;
    };

    const renderLabel = (entry) => {
        return `${entry.value}`;
    };

    return (
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">Severity Breakdown</h2>
                <Shield className="w-5 h-5 text-slate-400" />
            </div>

            <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={renderLabel}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ fontSize: 12 }}
                        formatter={(value, entry) => (
                            <span style={{ color: entry.color }}>{value}</span>
                        )}
                    />
                </PieChart>
            </ResponsiveContainer>

            <div className="mt-4 grid grid-cols-2 gap-3">
                {data.map((item) => (
                    <div key={item.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                            <span className="text-sm text-slate-300">{item.name}</span>
                        </div>
                        <span className="text-sm font-bold text-white">{item.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
