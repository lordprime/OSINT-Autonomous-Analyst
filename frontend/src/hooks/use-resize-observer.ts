import { useEffect, useState, RefObject } from 'react'

interface ResizeObserverEntry {
    target: Element
    contentRect: DOMRectReadOnly
}

export function useResizeObserver(elementRef: RefObject<Element>): ResizeObserverEntry | undefined {
    const [entry, setEntry] = useState<ResizeObserverEntry>()

    useEffect(() => {
        const node = elementRef?.current
        if (!node) return

        const observer = new ResizeObserver(([entry]) => setEntry(entry))
        observer.observe(node)

        return () => observer.disconnect()
    }, [elementRef])

    return entry
}
