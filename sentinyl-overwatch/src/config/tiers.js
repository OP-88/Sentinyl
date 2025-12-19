/**
 * Sentinyl Subscription Tiers Configuration
 * 
 * Centralized configuration for pricing, features, and quotas.
 * Easy to update when pricing or features change.
 */

export const TIER_CONFIG = {
    free: {
        id: 'free',
        name: 'Free',
        price: 0,
        billingPeriod: null,
        features: {
            scout: true,  // Limited scans
            guard: false,
            ghost: false,
            lazarus: false
        },
        quotas: {
            scansPerMonth: 5,
            agents: 0
        },
        description: 'Basic threat detection for small teams'
    },
    scout_pro: {
        id: 'scout_pro',
        name: 'Scout Pro',
        price: 49,
        billingPeriod: 'month',
        features: {
            scout: true,
            guard: false,
            ghost: false,
            lazarus: false
        },
        quotas: {
            scansPerMonth: 'unlimited',
            agents: 0
        },
        description: 'Unlimited external threat monitoring'
    },
    guard_lite: {
        id: 'guard_lite',
        name: 'Guard Lite',
        price: 29,
        billingPeriod: 'month',
        features: {
            scout: false,
            guard: true,
            ghost: true,
            lazarus: true
        },
        quotas: {
            scansPerMonth: 0,
            agents: 3
        },
        description: 'Infrastructure protection for up to 3 servers'
    },
    full_stack: {
        id: 'full_stack',
        name: 'Full Stack',
        price: 99,
        billingPeriod: 'month',
        features: {
            scout: true,
            guard: true,
            ghost: true,
            lazarus: true
        },
        quotas: {
            scansPerMonth: 'unlimited',
            agents: 'unlimited'
        },
        description: 'Complete security platform with all features'
    }
};

/**
 * Get feature access based on tier
 */
export const getFeatureAccess = (tierId) => {
    const tier = TIER_CONFIG[tierId] || TIER_CONFIG.free;

    return {
        hasScout: tier.features.scout,
        hasGuard: tier.features.guard,
        hasGhost: tier.features.ghost,
        hasLazarus: tier.features.lazarus,
        tier: tier.id,
        tierName: tier.name,
        price: tier.price,
        billingPeriod: tier.billingPeriod,
        quotas: tier.quotas
    };
};

/**
 * Get all available tiers for pricing page
 */
export const getAllTiers = () => {
    return Object.values(TIER_CONFIG);
};

/**
 * Check if a specific feature is available for a tier
 */
export const hasFeature = (tierId, feature) => {
    const tier = TIER_CONFIG[tierId] || TIER_CONFIG.free;
    return tier.features[feature] || false;
};
