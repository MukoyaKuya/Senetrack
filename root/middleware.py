from django.conf import settings

class ContentSecurityPolicyMiddleware:
    """
    Simple middleware to inject Content-Security-Policy (CSP) headers.
    Uses settings defined in settings.py (CSP_*).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if not getattr(settings, 'DEBUG', True):
            policies = []
            if hasattr(settings, 'CSP_DEFAULT_SRC'):
                policies.append(f"default-src {' '.join(settings.CSP_DEFAULT_SRC)}")
            if hasattr(settings, 'CSP_STYLE_SRC'):
                policies.append(f"style-src {' '.join(settings.CSP_STYLE_SRC)}")
            if hasattr(settings, 'CSP_SCRIPT_SRC'):
                policies.append(f"script-src {' '.join(settings.CSP_SCRIPT_SRC)}")
            if hasattr(settings, 'CSP_IMG_SRC'):
                policies.append(f"img-src {' '.join(settings.CSP_IMG_SRC)}")
            if hasattr(settings, 'CSP_FONT_SRC'):
                policies.append(f"font-src {' '.join(settings.CSP_FONT_SRC)}")
            if hasattr(settings, 'CSP_CONNECT_SRC'):
                policies.append(f"connect-src {' '.join(settings.CSP_CONNECT_SRC)}")
            if hasattr(settings, 'CSP_WORKER_SRC'):
                policies.append(f"worker-src {' '.join(settings.CSP_WORKER_SRC)}")
            if hasattr(settings, 'CSP_FRAME_ANCESTORS'):
                policies.append(f"frame-ancestors {' '.join(settings.CSP_FRAME_ANCESTORS)}")
            
            if policies:
                response["Content-Security-Policy"] = "; ".join(policies)
        
        return response
