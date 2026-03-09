import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { IconDefinition } from '@fortawesome/fontawesome-svg-core'
import { faSpinner } from '@fortawesome/free-solid-svg-icons'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-primary-500 text-white hover:bg-primary-600 active:bg-primary-700 focus:ring-primary-500 shadow-sm',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-slate-200 dark:border-slate-700 focus:ring-primary-500',
        ghost: 'hover:bg-accent hover:text-accent-foreground text-slate-600 dark:text-slate-400 focus:ring-primary-500',
        danger: 'bg-error-solid text-white hover:bg-red-600 active:bg-red-700 focus:ring-red-500 shadow-sm',
        // Landing specific aliases / variants
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
        hero: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all duration-300',
        heroOutline: 'border-2 border-primary/50 bg-transparent text-foreground hover:bg-primary/10 hover:border-primary transition-all duration-300',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'px-3 py-1.5 text-xs gap-1.5',
        md: 'px-4 py-2.5 text-sm gap-2',
        lg: 'px-5 py-3 text-base gap-2.5',
        xl: 'h-14 rounded-xl px-8 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  icon?: IconDefinition
  iconPosition?: 'left' | 'right'
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, icon, iconPosition = 'left', loading, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    
    // Support children as a function or Slot's complex children if asChild is true
    // But for simplicity, we just render normally if not loading
    
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={props.disabled || loading}
        {...props}
      >
        {loading ? (
          <FontAwesomeIcon icon={faSpinner} className="animate-spin" />
        ) : icon && iconPosition === 'left' ? (
          <FontAwesomeIcon icon={icon} className="text-[0.85em]" />
        ) : null}
        {children}
        {!loading && icon && iconPosition === 'right' && (
          <FontAwesomeIcon icon={icon} className="text-[0.85em]" />
        )}
      </Comp>
    )
  }
)
Button.displayName = 'Button'

// Export as LandingButton for compatibility
const LandingButton = Button;

export { Button, LandingButton, buttonVariants }
