import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';

/**
 * Toast Component - Notification toast for user feedback
 * 
 * Types: success, error, warning, info
 */
export default function Toast({ message, type = 'info', onClose }) {
    const icons = {
        success: <CheckCircle className="w-5 h-5" />,
        error: <AlertCircle className="w-5 h-5" />,
        warning: <AlertTriangle className="w-5 h-5" />,
        info: <Info className="w-5 h-5" />
    };

    const styles = {
        success: 'bg-green-500/10 border-green-500/50 text-green-400',
        error: 'bg-red-500/10 border-red-500/50 text-red-400',
        warning: 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400',
        info: 'bg-blue-500/10 border-blue-500/50 text-blue-400'
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, x: 100, scale: 0.8 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 100, scale: 0.8 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className={`
                    min-w-[320px] max-w-md p-4 rounded-lg border backdrop-blur-sm
                    flex items-start gap-3 shadow-2xl
                    ${styles[type]}
                `}
            >
                <div className="flex-shrink-0 mt-0.5">
                    {icons[type]}
                </div>
                <p className="flex-1 text-sm font-medium text-white">
                    {message}
                </p>
                <button
                    onClick={onClose}
                    className="flex-shrink-0 text-slate-400 hover:text-white transition-colors"
                    aria-label="Close notification"
                >
                    <X className="w-4 h-4" />
                </button>
            </motion.div>
        </AnimatePresence>
    );
}
