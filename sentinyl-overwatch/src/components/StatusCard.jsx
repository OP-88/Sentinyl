import { motion } from 'framer-motion';

/**
 * StatusCard - Reusable stat display component
 * 
 * Shows system metrics with cyberpunk glow effects
 * and pulsing online indicators.
 */
export default function StatusCard({
    title,
    value,
    icon: Icon,
    status = 'OFFLINE',
    description,
    pulse = false
}) {
    const isOnline = status === 'ONLINE';
    const isCritical = status === 'CRITICAL';

    const borderColor = isCritical
        ? 'border-red-500/50 hover:border-red-400'
        : isOnline
            ? 'border-green-500/50 hover:border-green-400'
            : 'border-gray-700 hover:border-gray-600';

    const glowColor = isCritical
        ? 'shadow-red-500/20 hover:shadow-red-500/60 hover:shadow-2xl hover:shadow-[0_0_30px_rgba(239,68,68,0.5)]'
        : isOnline
            ? 'shadow-green-500/20 hover:shadow-green-500/60 hover:shadow-2xl hover:shadow-[0_0_30px_rgba(34,197,94,0.5)]'
            : 'shadow-gray-900/20 hover:shadow-gray-700/40 hover:shadow-[0_0_20px_rgba(100,116,139,0.3)]';

    return (
        <div
            className={`
        bg-gray-900 rounded-lg border ${borderColor} 
        ${glowColor} shadow-lg p-4 
        hover:bg-gray-800/50
        transition-all duration-300
        relative overflow-hidden
        cursor-pointer
      `}
        >
            {/* Animated background gradient */}
            {isOnline && (
                <motion.div
                    className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-transparent"
                    animate={{
                        opacity: [0.3, 0.6, 0.3]
                    }}
                    transition={{
                        repeat: Infinity,
                        duration: 3
                    }}
                />
            )}

            {/* Content */}
            <div className="relative z-10">
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        {Icon && <Icon className="w-5 h-5 text-cyan-400" />}
                        <h3 className="text-gray-400 text-xs font-mono uppercase tracking-wider">
                            {title}
                        </h3>
                    </div>

                    {/* Status Indicator */}
                    {pulse && (
                        <div className="flex items-center gap-2">
                            <motion.div
                                className={`w-2 h-2 rounded-full ${isCritical
                                    ? 'bg-red-500'
                                    : isOnline
                                        ? 'bg-green-500'
                                        : 'bg-gray-600'
                                    }`}
                                animate={isOnline || isCritical ? {
                                    opacity: [1, 0.5, 1]
                                } : {}}
                                transition={{
                                    repeat: Infinity,
                                    duration: 2
                                }}
                            />
                            <span className={`text-xs font-mono ${isCritical
                                ? 'text-red-400'
                                : isOnline
                                    ? 'text-green-400'
                                    : 'text-gray-500'
                                }`}>
                                {status}
                            </span>
                        </div>
                    )}
                </div>

                {/* Value */}
                <div className="mb-2">
                    <motion.div
                        key={value}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className={`text-3xl font-bold font-mono ${isCritical
                            ? 'text-red-400'
                            : isOnline
                                ? 'text-green-400'
                                : 'text-cyan-400'
                            }`}
                    >
                        {value}
                    </motion.div>
                </div>

                {/* Description */}
                {description && (
                    <p className="text-gray-500 text-xs font-mono">
                        {description}
                    </p>
                )}
            </div>

            {/* Scan line effect */}
            {isOnline && (
                <motion.div
                    className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-green-500/50 to-transparent"
                    animate={{
                        top: ['0%', '100%']
                    }}
                    transition={{
                        repeat: Infinity,
                        duration: 4,
                        ease: 'linear'
                    }}
                />
            )}
        </div>
    );
}
