import { useUser } from '../context/UserContext';

/**
 * useTierAccess - Hook for tier-based feature access
 * 
 * Returns feature flags based on user's subscription tier
 */
export const useTierAccess = () => {
    const { hasScout, hasGuard, hasGhost, hasLazarus, tier } = useUser();

    return {
        hasScout,
        hasGuard,
        hasGhost,
        hasLazarus,
        tier,
        isFree: tier === 'free',
        isScoutPro: tier === 'scout_pro',
        isGuardLite: tier === 'guard_lite',
        isFullStack: tier === 'full_stack',
        canAccessScout: hasScout,
        canAccessGuard: hasGuard,
        canAccessGhost: hasGhost,
        canAccessLazarus: hasLazarus
    };
};
