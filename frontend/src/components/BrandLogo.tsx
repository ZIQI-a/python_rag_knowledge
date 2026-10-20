import {BRAND} from '@/config/brand'
import {PALETTE} from '@/config/theme'

interface BrandLogoProps {
    size?: number
    showText?: boolean
    inverse?: boolean
}

/** 共用「渡口书页」标识；紧凑模式用于折叠侧栏。 */
export function BrandLogo({size = 36, showText = true, inverse = false}: BrandLogoProps) {
    return (
        <span style={{display: 'inline-flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap'}}>
            <img src={BRAND.logoSrc} width={size} height={size} alt="" aria-hidden="true"
                 style={{display: 'block', flexShrink: 0}}/>
            {showText && (
                <span style={{color: inverse ? PALETTE.white : PALETTE.ink, fontSize: 22,
                    fontWeight: 600, letterSpacing: 3, lineHeight: 1,
                    fontFamily: '"Songti SC", "STSong", serif'}}>
                    {BRAND.name}
                </span>
            )}
        </span>
    )
}
