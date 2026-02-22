"""
Ribbon Message Listener - Custom Component

Questo component è invisibile e contiene SOLO il listener JavaScript
per i messaggi della ribbon. Viene renderizzato come st.components.html()
con height=0 in modo da non occupare spazio visibile.
"""

import streamlit.components.v1 as components


def render_listener():
    """
    Render an invisible listener component for ribbon postMessages.

    This uses st.components.html() which properly injects JavaScript
    into the main window context, unlike st.markdown() or st.write().
    """
    listener_html = """
<!DOCTYPE html>
<html>
<head>
    <script>
    console.log('=== RIBBON LISTENER COMPONENT LOADED ===');
    console.log('Location:', window.location.href);
    console.log('Window.top === window:', window.top === window);

    // Add listener to window.top (the main Streamlit window)
    // This works even if this script runs in an iframe
    console.log('✓ Attaching listener to window and window.top');

    // Listen on window
    window.addEventListener('message', function(event) {
        handleRibbonMessage(event);
    });

    // Also listen on window.top
    if (window.top && window.top !== window) {
        window.top.addEventListener('message', function(event) {
            handleRibbonMessage(event);
        });
    }

    function handleRibbonMessage(event) {
        console.log('✓ LISTENER: Received postMessage');
        console.log('  - Type:', event.data?.type);
        console.log('  - Data:', event.data);

        // Handle both 'ribbon-tab' and 'ribbon-navigate' messages
        if (event.data && (event.data.type === 'ribbon-tab' || event.data.type === 'ribbon-navigate')) {
            const tabName = event.data.active_ribbon_tab;
            console.log('✓ LISTENER: Processing tab change to:', tabName);

            try {
                // Try to navigate window.parent (Streamlit main window)
                const url = new URL(window.parent.location);
                url.searchParams.set('active_ribbon_tab', tabName);
                console.log('✓ LISTENER: Navigating parent to:', url.toString());
                window.parent.location.href = url.toString();
            } catch (e) {
                console.log('✓ LISTENER: Cannot navigate parent:', e.message);

                // Fallback: try window.top
                try {
                    const url = new URL(window.top.location);
                    url.searchParams.set('active_ribbon_tab', tabName);
                    console.log('✓ LISTENER: Navigating window.top to:', url.toString());
                    window.top.location.href = url.toString();
                } catch (e2) {
                    console.error('✓ LISTENER: Cannot navigate window.top:', e2.message);
                }
            }
        }
    }

    console.log('✓ Listener initialized');
    </script>
</head>
<body>
    <!-- Invisible component - just for JavaScript injection -->
</body>
</html>
"""

    # Render with height=0 to make it invisible
    components.html(listener_html, height=0, scrolling=False)
