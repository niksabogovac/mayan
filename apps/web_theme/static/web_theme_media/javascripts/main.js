if (typeof String.prototype.startsWith != 'function') {
	  String.prototype.startsWith = function (str){
	    return this.indexOf(str) == 0;
	  };
	}

if (typeof String.prototype.replaceBetween != 'function') {
	String.prototype.replaceBetween = function(start, end, what) {
	    return this.substring(0, start) + what + this.substring(end);
	};
}