// Simple toast hook using native alert for now
// TODO: Implement proper toast UI with Radix UI Toast

export function useToast() {
  return {
    toast: ({
      title,
      description,
      variant,
    }: {
      title: string
      description?: string
      variant?: 'default' | 'destructive'
    }) => {
      const message = description ? `${title}\n${description}` : title

      if (variant === 'destructive') {
        console.error(message)
      } else {
        console.log(message)
      }

      // Optionally show native alert for important messages
      // Uncomment if you want visual feedback
      // alert(message)
    },
  }
}
